"""Pluggable Rules Engine Service for NextGen Fusion Platform

Provides dynamic compliance rule execution:
- Rule evaluation with multiple execution strategies
- Condition parsing and evaluation
- Action execution and result handling
- Performance monitoring and caching
- Extensible rule types and custom functions
"""

import asyncio
import json
import re
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Callable, Set
from dataclasses import dataclass
from enum import Enum
import jsonpath_ng
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from ..models.rules_engine import (
    ComplianceRule, RuleCondition, RuleAction, RuleExecution, RuleViolation,
    RuleSet, RuleSetMembership, ComplianceJurisdiction,
    RuleStatus, ConditionOperator, RuleSeverity, ExecutionResult
)
from shared.database.session import get_async_session
from shared.cache.redis_cache import cached, CacheManager

logger = logging.getLogger(__name__)


@dataclass
class EvaluationContext:
    """Context for rule evaluation"""
    entity_type: str
    entity_id: str
    entity_data: Dict[str, Any]
    jurisdiction_codes: List[str]
    user_id: Optional[str] = None
    execution_context: str = "default"
    metadata: Dict[str, Any] = None


@dataclass
class ConditionResult:
    """Result of condition evaluation"""
    condition_id: str
    passed: bool
    actual_value: Any
    expected_value: Any
    message: str
    field_path: str


@dataclass
class RuleResult:
    """Result of rule execution"""
    rule_id: str
    rule_code: str
    passed: bool
    result: ExecutionResult
    execution_time_ms: int
    condition_results: List[ConditionResult]
    violations: List[Dict[str, Any]]
    actions_executed: List[Dict[str, Any]]
    error_message: Optional[str] = None


@dataclass
class RuleSetResult:
    """Result of rule set execution"""
    rule_set_id: str
    rule_set_name: str
    overall_passed: bool
    total_rules: int
    passed_rules: int
    failed_rules: int
    execution_time_ms: int
    rule_results: List[RuleResult]
    stopped_early: bool = False


class ExecutionStrategy(str, Enum):
    """Rule execution strategies"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FAIL_FAST = "fail_fast"


class RulesEngineService:
    """Service for executing compliance rules"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.custom_functions: Dict[str, Callable] = {}
        self.condition_evaluators: Dict[str, Callable] = {
            ConditionOperator.EQUALS: self._evaluate_equals,
            ConditionOperator.NOT_EQUALS: self._evaluate_not_equals,
            ConditionOperator.GREATER_THAN: self._evaluate_greater_than,
            ConditionOperator.GREATER_THAN_OR_EQUAL: self._evaluate_greater_than_or_equal,
            ConditionOperator.LESS_THAN: self._evaluate_less_than,
            ConditionOperator.LESS_THAN_OR_EQUAL: self._evaluate_less_than_or_equal,
            ConditionOperator.CONTAINS: self._evaluate_contains,
            ConditionOperator.NOT_CONTAINS: self._evaluate_not_contains,
            ConditionOperator.IN: self._evaluate_in,
            ConditionOperator.NOT_IN: self._evaluate_not_in,
            ConditionOperator.REGEX_MATCH: self._evaluate_regex_match,
            ConditionOperator.BETWEEN: self._evaluate_between,
            ConditionOperator.IS_NULL: self._evaluate_is_null,
            ConditionOperator.IS_NOT_NULL: self._evaluate_is_not_null,
        }
        self.action_handlers: Dict[str, Callable] = {
            "validate": self._handle_validate_action,
            "transform": self._handle_transform_action,
            "notify": self._handle_notify_action,
            "block": self._handle_block_action,
            "log": self._handle_log_action,
        }
    
    def register_custom_function(self, name: str, function: Callable):
        """Register a custom function for use in rule expressions"""
        self.custom_functions[name] = function
    
    def register_action_handler(self, action_type: str, handler: Callable):
        """Register a custom action handler"""
        self.action_handlers[action_type] = handler
    
    async def evaluate_rule_set(
        self, 
        rule_set_id: str, 
        context: EvaluationContext,
        strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    ) -> RuleSetResult:
        """Evaluate a complete rule set"""
        start_time = datetime.utcnow()
        
        async with get_async_session() as session:
            # Load rule set with rules
            rule_set_query = select(RuleSet).where(
                and_(
                    RuleSet.id == rule_set_id,
                    RuleSet.is_active == True
                )
            ).options(
                selectinload(RuleSet.rule_memberships).selectinload(RuleSetMembership.rule)
            )
            
            rule_set_result = await session.execute(rule_set_query)
            rule_set = rule_set_result.scalar_one_or_none()
            
            if not rule_set:
                raise ValueError(f"Rule set {rule_set_id} not found or inactive")
            
            # Get active rules in execution order
            active_memberships = [
                membership for membership in rule_set.rule_memberships
                if membership.is_active and membership.rule.is_active()
            ]
            active_memberships.sort(key=lambda m: m.execution_order)
            
            rule_results = []
            passed_rules = 0
            failed_rules = 0
            stopped_early = False
            
            # Execute rules based on strategy
            if strategy == ExecutionStrategy.PARALLEL:
                # Execute all rules in parallel
                tasks = [
                    self.evaluate_rule(membership.rule.id, context)
                    for membership in active_memberships
                ]
                rule_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle exceptions
                for i, result in enumerate(rule_results):
                    if isinstance(result, Exception):
                        rule_results[i] = RuleResult(
                            rule_id=str(active_memberships[i].rule.id),
                            rule_code=active_memberships[i].rule.rule_code,
                            passed=False,
                            result=ExecutionResult.ERROR,
                            execution_time_ms=0,
                            condition_results=[],
                            violations=[],
                            actions_executed=[],
                            error_message=str(result)
                        )
                        failed_rules += 1
                    elif result.passed:
                        passed_rules += 1
                    else:
                        failed_rules += 1
            
            else:
                # Sequential execution (default)
                for membership in active_memberships:
                    try:
                        result = await self.evaluate_rule(membership.rule.id, context)
                        rule_results.append(result)
                        
                        if result.passed:
                            passed_rules += 1
                        else:
                            failed_rules += 1
                            
                            # Check if we should stop on first failure
                            if (rule_set.stop_on_first_failure or 
                                strategy == ExecutionStrategy.FAIL_FAST):
                                stopped_early = True
                                break
                    
                    except Exception as e:
                        logger.error(f"Error executing rule {membership.rule.id}: {e}")
                        error_result = RuleResult(
                            rule_id=str(membership.rule.id),
                            rule_code=membership.rule.rule_code,
                            passed=False,
                            result=ExecutionResult.ERROR,
                            execution_time_ms=0,
                            condition_results=[],
                            violations=[],
                            actions_executed=[],
                            error_message=str(e)
                        )
                        rule_results.append(error_result)
                        failed_rules += 1
                        
                        if rule_set.stop_on_first_failure:
                            stopped_early = True
                            break
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            overall_passed = failed_rules == 0
            
            return RuleSetResult(
                rule_set_id=str(rule_set.id),
                rule_set_name=rule_set.name,
                overall_passed=overall_passed,
                total_rules=len(active_memberships),
                passed_rules=passed_rules,
                failed_rules=failed_rules,
                execution_time_ms=execution_time_ms,
                rule_results=rule_results,
                stopped_early=stopped_early
            )
    
    async def evaluate_rule(self, rule_id: str, context: EvaluationContext) -> RuleResult:
        """Evaluate a single compliance rule"""
        start_time = datetime.utcnow()
        
        async with get_async_session() as session:
            # Load rule with conditions and actions
            rule_query = select(ComplianceRule).where(
                ComplianceRule.id == rule_id
            ).options(
                selectinload(ComplianceRule.conditions_rel),
                selectinload(ComplianceRule.actions)
            )
            
            rule_result = await session.execute(rule_query)
            rule = rule_result.scalar_one_or_none()
            
            if not rule:
                raise ValueError(f"Rule {rule_id} not found")
            
            if not rule.is_active():
                return RuleResult(
                    rule_id=str(rule.id),
                    rule_code=rule.rule_code,
                    passed=True,
                    result=ExecutionResult.SKIPPED,
                    execution_time_ms=0,
                    condition_results=[],
                    violations=[],
                    actions_executed=[]
                )
            
            try:
                # Evaluate conditions
                condition_results = await self._evaluate_conditions(rule, context)
                
                # Determine if rule passed
                passed = all(cr.passed for cr in condition_results)
                result_status = ExecutionResult.PASS if passed else ExecutionResult.FAIL
                
                # Create violations for failed conditions
                violations = []
                for cr in condition_results:
                    if not cr.passed:
                        violations.append({
                            'condition_id': cr.condition_id,
                            'field_path': cr.field_path,
                            'message': cr.message,
                            'expected_value': cr.expected_value,
                            'actual_value': cr.actual_value,
                            'severity': rule.severity
                        })
                
                # Execute actions
                actions_executed = await self._execute_actions(rule, context, passed)
                
                end_time = datetime.utcnow()
                execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Record execution
                await self._record_execution(
                    session, rule, context, result_status, 
                    condition_results, violations, execution_time_ms
                )
                
                return RuleResult(
                    rule_id=str(rule.id),
                    rule_code=rule.rule_code,
                    passed=passed,
                    result=result_status,
                    execution_time_ms=execution_time_ms,
                    condition_results=condition_results,
                    violations=violations,
                    actions_executed=actions_executed
                )
            
            except Exception as e:
                end_time = datetime.utcnow()
                execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                logger.error(f"Error executing rule {rule.rule_code}: {e}")
                
                # Record failed execution
                await self._record_execution(
                    session, rule, context, ExecutionResult.ERROR, 
                    [], [], execution_time_ms, str(e)
                )
                
                return RuleResult(
                    rule_id=str(rule.id),
                    rule_code=rule.rule_code,
                    passed=False,
                    result=ExecutionResult.ERROR,
                    execution_time_ms=execution_time_ms,
                    condition_results=[],
                    violations=[],
                    actions_executed=[],
                    error_message=str(e)
                )
    
    async def _evaluate_conditions(
        self, 
        rule: ComplianceRule, 
        context: EvaluationContext
    ) -> List[ConditionResult]:
        """Evaluate all conditions for a rule"""
        condition_results = []
        
        # Group conditions by logical operator
        condition_groups = {}
        for condition in rule.conditions_rel:
            if not condition.is_active:
                continue
            
            group = condition.condition_group or "default"
            if group not in condition_groups:
                condition_groups[group] = []
            condition_groups[group].append(condition)
        
        # Evaluate each group
        for group_name, conditions in condition_groups.items():
            group_results = []
            
            for condition in conditions:
                try:
                    # Extract value from entity data using field path
                    actual_value = self._extract_field_value(
                        context.entity_data, condition.field_path
                    )
                    
                    # Evaluate condition
                    evaluator = self.condition_evaluators.get(condition.operator)
                    if not evaluator:
                        raise ValueError(f"Unknown condition operator: {condition.operator}")
                    
                    passed = evaluator(actual_value, condition.expected_value)
                    
                    message = (
                        f"Condition passed: {condition.field_path} {condition.operator} {condition.expected_value}"
                        if passed else
                        f"Condition failed: {condition.field_path} {condition.operator} {condition.expected_value} "
                        f"(actual: {actual_value})"
                    )
                    
                    result = ConditionResult(
                        condition_id=str(condition.id),
                        passed=passed,
                        actual_value=actual_value,
                        expected_value=condition.expected_value,
                        message=message,
                        field_path=condition.field_path
                    )
                    
                    group_results.append(result)
                    condition_results.append(result)
                
                except Exception as e:
                    logger.error(f"Error evaluating condition {condition.id}: {e}")
                    result = ConditionResult(
                        condition_id=str(condition.id),
                        passed=False,
                        actual_value=None,
                        expected_value=condition.expected_value,
                        message=f"Evaluation error: {str(e)}",
                        field_path=condition.field_path
                    )
                    group_results.append(result)
                    condition_results.append(result)
        
        return condition_results
    
    def _extract_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Extract value from data using field path (JSONPath or dot notation)"""
        try:
            # Try JSONPath first
            if field_path.startswith('$'):
                jsonpath_expr = jsonpath_ng.parse(field_path)
                matches = jsonpath_expr.find(data)
                return matches[0].value if matches else None
            
            # Fall back to dot notation
            keys = field_path.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                elif isinstance(value, list) and key.isdigit():
                    index = int(key)
                    value = value[index] if 0 <= index < len(value) else None
                else:
                    return None
                
                if value is None:
                    break
            
            return value
        
        except Exception as e:
            logger.warning(f"Error extracting field {field_path}: {e}")
            return None
    
    # Condition evaluators
    def _evaluate_equals(self, actual: Any, expected: Any) -> bool:
        return actual == expected
    
    def _evaluate_not_equals(self, actual: Any, expected: Any) -> bool:
        return actual != expected
    
    def _evaluate_greater_than(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    
    def _evaluate_greater_than_or_equal(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) >= float(expected)
        except (TypeError, ValueError):
            return False
    
    def _evaluate_less_than(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    
    def _evaluate_less_than_or_equal(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) <= float(expected)
        except (TypeError, ValueError):
            return False
    
    def _evaluate_contains(self, actual: Any, expected: Any) -> bool:
        try:
            return expected in actual
        except TypeError:
            return False
    
    def _evaluate_not_contains(self, actual: Any, expected: Any) -> bool:
        try:
            return expected not in actual
        except TypeError:
            return True
    
    def _evaluate_in(self, actual: Any, expected: Any) -> bool:
        try:
            if isinstance(expected, list):
                return actual in expected
            return False
        except TypeError:
            return False
    
    def _evaluate_not_in(self, actual: Any, expected: Any) -> bool:
        try:
            if isinstance(expected, list):
                return actual not in expected
            return True
        except TypeError:
            return True
    
    def _evaluate_regex_match(self, actual: Any, expected: Any) -> bool:
        try:
            pattern = str(expected)
            text = str(actual)
            return bool(re.match(pattern, text))
        except (TypeError, re.error):
            return False
    
    def _evaluate_between(self, actual: Any, expected: Any) -> bool:
        try:
            if isinstance(expected, list) and len(expected) == 2:
                min_val, max_val = expected
                return float(min_val) <= float(actual) <= float(max_val)
            return False
        except (TypeError, ValueError):
            return False
    
    def _evaluate_is_null(self, actual: Any, expected: Any) -> bool:
        return actual is None
    
    def _evaluate_is_not_null(self, actual: Any, expected: Any) -> bool:
        return actual is not None
    
    async def _execute_actions(
        self, 
        rule: ComplianceRule, 
        context: EvaluationContext, 
        rule_passed: bool
    ) -> List[Dict[str, Any]]:
        """Execute rule actions"""
        actions_executed = []
        
        # Sort actions by execution order
        active_actions = [a for a in rule.actions if a.is_active]
        active_actions.sort(key=lambda a: a.execution_order)
        
        for action in active_actions:
            try:
                handler = self.action_handlers.get(action.action_type)
                if not handler:
                    logger.warning(f"No handler for action type: {action.action_type}")
                    continue
                
                result = await handler(action, context, rule_passed)
                actions_executed.append({
                    'action_id': str(action.id),
                    'action_type': action.action_type,
                    'result': result,
                    'executed_at': datetime.utcnow().isoformat()
                })
            
            except Exception as e:
                logger.error(f"Error executing action {action.id}: {e}")
                actions_executed.append({
                    'action_id': str(action.id),
                    'action_type': action.action_type,
                    'result': {'error': str(e)},
                    'executed_at': datetime.utcnow().isoformat()
                })
        
        return actions_executed
    
    # Action handlers
    async def _handle_validate_action(self, action: RuleAction, context: EvaluationContext, rule_passed: bool) -> Dict[str, Any]:
        """Handle validation action"""
        return {
            'type': 'validation',
            'passed': rule_passed,
            'message': action.action_config.get('message', 'Validation completed')
        }
    
    async def _handle_transform_action(self, action: RuleAction, context: EvaluationContext, rule_passed: bool) -> Dict[str, Any]:
        """Handle data transformation action"""
        # This would implement data transformation logic
        return {
            'type': 'transformation',
            'applied': rule_passed,
            'config': action.action_config
        }
    
    async def _handle_notify_action(self, action: RuleAction, context: EvaluationContext, rule_passed: bool) -> Dict[str, Any]:
        """Handle notification action"""
        # This would send notifications (email, webhook, etc.)
        return {
            'type': 'notification',
            'sent': True,
            'recipients': action.action_config.get('recipients', []),
            'message': action.action_config.get('message', 'Rule notification')
        }
    
    async def _handle_block_action(self, action: RuleAction, context: EvaluationContext, rule_passed: bool) -> Dict[str, Any]:
        """Handle blocking action"""
        return {
            'type': 'block',
            'blocked': not rule_passed,
            'reason': action.action_config.get('reason', 'Rule violation')
        }
    
    async def _handle_log_action(self, action: RuleAction, context: EvaluationContext, rule_passed: bool) -> Dict[str, Any]:
        """Handle logging action"""
        log_level = action.action_config.get('level', 'info')
        message = action.action_config.get('message', f'Rule execution: {rule_passed}')
        
        if log_level == 'error':
            logger.error(message)
        elif log_level == 'warning':
            logger.warning(message)
        else:
            logger.info(message)
        
        return {
            'type': 'log',
            'logged': True,
            'level': log_level,
            'message': message
        }
    
    async def _record_execution(
        self,
        session: AsyncSession,
        rule: ComplianceRule,
        context: EvaluationContext,
        result: ExecutionResult,
        condition_results: List[ConditionResult],
        violations: List[Dict[str, Any]],
        execution_time_ms: int,
        error_message: Optional[str] = None
    ):
        """Record rule execution in database"""
        execution = RuleExecution(
            rule_id=rule.id,
            execution_context=context.execution_context,
            target_entity_type=context.entity_type,
            target_entity_id=context.entity_id,
            result=result,
            passed_conditions=sum(1 for cr in condition_results if cr.passed),
            failed_conditions=sum(1 for cr in condition_results if not cr.passed),
            input_data=context.entity_data,
            output_data={
                'condition_results': [{
                    'condition_id': cr.condition_id,
                    'passed': cr.passed,
                    'actual_value': cr.actual_value,
                    'expected_value': cr.expected_value
                } for cr in condition_results]
            },
            error_details={'message': error_message} if error_message else None,
            executed_by_user_id=context.user_id,
            execution_version=rule.version,
            execution_time_ms=execution_time_ms,
            completed_at=datetime.utcnow()
        )
        
        session.add(execution)
        await session.flush()  # Get execution ID
        
        # Record violations
        for violation_data in violations:
            violation = RuleViolation(
                execution_id=execution.id,
                violation_type=violation_data.get('field_path', 'unknown'),
                severity=violation_data.get('severity', RuleSeverity.WARNING),
                message=violation_data['message'],
                field_path=violation_data.get('field_path'),
                expected_value=violation_data.get('expected_value'),
                actual_value=violation_data.get('actual_value')
            )
            session.add(violation)
        
        await session.commit()
    
    @cached(namespace="rules_by_jurisdiction", ttl=3600)
    async def get_rules_for_jurisdiction(
        self, 
        jurisdiction_codes: List[str], 
        rule_types: Optional[List[str]] = None
    ) -> List[ComplianceRule]:
        """Get active rules for specific jurisdictions"""
        async with get_async_session() as session:
            query = select(ComplianceRule).join(
                ComplianceJurisdiction
            ).where(
                and_(
                    ComplianceJurisdiction.code.in_(jurisdiction_codes),
                    ComplianceRule.status == RuleStatus.ACTIVE,
                    or_(
                        ComplianceRule.effective_date.is_(None),
                        ComplianceRule.effective_date <= datetime.utcnow()
                    ),
                    or_(
                        ComplianceRule.expiry_date.is_(None),
                        ComplianceRule.expiry_date > datetime.utcnow()
                    )
                )
            )
            
            if rule_types:
                query = query.where(ComplianceRule.rule_type.in_(rule_types))
            
            query = query.order_by(ComplianceRule.execution_order)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def validate_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        entity_data: Dict[str, Any],
        jurisdiction_codes: List[str],
        rule_types: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> RuleSetResult:
        """Validate an entity against applicable rules"""
        context = EvaluationContext(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_data=entity_data,
            jurisdiction_codes=jurisdiction_codes,
            user_id=user_id,
            execution_context="entity_validation"
        )
        
        # Get applicable rules
        rules = await self.get_rules_for_jurisdiction(jurisdiction_codes, rule_types)
        
        # Execute rules
        start_time = datetime.utcnow()
        rule_results = []
        passed_rules = 0
        failed_rules = 0
        
        for rule in rules:
            try:
                result = await self.evaluate_rule(str(rule.id), context)
                rule_results.append(result)
                
                if result.passed:
                    passed_rules += 1
                else:
                    failed_rules += 1
            
            except Exception as e:
                logger.error(f"Error executing rule {rule.id}: {e}")
                error_result = RuleResult(
                    rule_id=str(rule.id),
                    rule_code=rule.rule_code,
                    passed=False,
                    result=ExecutionResult.ERROR,
                    execution_time_ms=0,
                    condition_results=[],
                    violations=[],
                    actions_executed=[],
                    error_message=str(e)
                )
                rule_results.append(error_result)
                failed_rules += 1
        
        end_time = datetime.utcnow()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return RuleSetResult(
            rule_set_id="ad_hoc_validation",
            rule_set_name=f"Validation for {entity_type}",
            overall_passed=failed_rules == 0,
            total_rules=len(rules),
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            execution_time_ms=execution_time_ms,
            rule_results=rule_results
        )


# Global service instance
rules_engine_service = RulesEngineService()