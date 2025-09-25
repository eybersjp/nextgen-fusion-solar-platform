# NextGen Fusion Solar Platform - Custom Agents Directory

## Overview

This directory contains the configuration files for five specialized AI agents designed for the NextGen Fusion Commercial Solar Platform. Each agent serves a specific role in the solar project lifecycle, from design and compliance to implementation and support.

## Agent Ecosystem

### 🛡️ @SpecOverseer
**Role**: Repository Integrity Guardian  
**File**: `spec-overseer.md`  
**Purpose**: Ensures absolute alignment with specifications, rules, and constitution. Guards code quality and blocks non-compliant changes.

**Key Responsibilities**:
- Specification compliance validation
- Type safety enforcement
- Test coverage monitoring
- Code quality gate enforcement

### ⚡ @SolarEngineer
**Role**: Solar & Battery Storage Systems Expert  
**File**: `solar-engineer.md`  
**Purpose**: Provides world-class solar and battery storage engineering expertise, from design to financial modeling.

**Key Responsibilities**:
- System design and optimization
- Financial modeling and analysis
- Performance predictions
- Bankable report generation

### 📋 @ComplianceBot
**Role**: Global Solar Regulations Specialist  
**File**: `compliance-bot.md`  
**Purpose**: Ensures compliance with global solar regulations across South Africa, Australia, and the United States.

**Key Responsibilities**:
- Multi-jurisdiction compliance analysis
- Permit package assembly
- Code violation identification
- Remediation planning

### 🔧 @SupportCopilot
**Role**: Expert Field Support Technician & AI Copilot  
**File**: `support-copilot.md`  
**Purpose**: Provides on-site installation, commissioning, and troubleshooting support for field personnel.

**Key Responsibilities**:
- Installation guidance
- Visual troubleshooting
- Safety protocol enforcement
- Documentation assistance

### 🏗️ @Builder
**Role**: Senior Full-Stack Software Engineer  
**File**: `builder.md`  
**Purpose**: Implements technical requirements through clean, efficient, and test-covered code across the entire stack.

**Key Responsibilities**:
- Feature implementation
- Code quality assurance
- Testing and validation
- Performance optimization

## Agent Interaction Matrix

| Agent | @SpecOverseer | @SolarEngineer | @ComplianceBot | @SupportCopilot | @Builder |
|-------|---------------|----------------|----------------|-----------------|----------|
| **@SpecOverseer** | - | Validates specs | Reviews compliance | Checks procedures | Enforces standards |
| **@SolarEngineer** | Submits designs | - | Requests compliance | Provides tech specs | Defines requirements |
| **@ComplianceBot** | Reports violations | Validates designs | - | Ensures field compliance | Reviews implementations |
| **@SupportCopilot** | Documents procedures | Clarifies specs | Confirms compliance | - | Reports field issues |
| **@Builder** | Follows standards | Implements designs | Codes compliance | Builds interfaces | - |

## Workflow Integration

### Design Phase
1. **@SolarEngineer** creates system design
2. **@ComplianceBot** validates regulatory compliance
3. **@SpecOverseer** ensures specification adherence
4. **@Builder** implements design requirements

### Implementation Phase
1. **@Builder** develops code and features
2. **@SpecOverseer** enforces quality gates
3. **@ComplianceBot** validates compliance implementation
4. **@SupportCopilot** prepares field documentation

### Deployment Phase
1. **@SupportCopilot** guides field installation
2. **@ComplianceBot** ensures permit compliance
3. **@SolarEngineer** validates performance
4. **@SpecOverseer** confirms final specifications

### Support Phase
1. **@SupportCopilot** handles field issues
2. **@SolarEngineer** analyzes performance data
3. **@Builder** implements fixes and updates
4. **@ComplianceBot** maintains ongoing compliance

## Technology Stack Coverage

### Frontend Development
- **Primary**: @Builder
- **Support**: @SpecOverseer (quality), @SupportCopilot (field interfaces)

### Backend Development
- **Primary**: @Builder
- **Support**: @SolarEngineer (domain logic), @ComplianceBot (regulatory APIs)

### Domain Expertise
- **Primary**: @SolarEngineer
- **Support**: @ComplianceBot (regulations), @SupportCopilot (field operations)

### Quality Assurance
- **Primary**: @SpecOverseer
- **Support**: All agents (domain-specific validation)

### Field Operations
- **Primary**: @SupportCopilot
- **Support**: @ComplianceBot (safety compliance), @SolarEngineer (technical guidance)

## Usage Guidelines

### Agent Invocation
```
@AgentName [command] [parameters]
```

### Multi-Agent Workflows
```
@SolarEngineer design --system=2MW_solar_4MWh_bess
@ComplianceBot check --jurisdiction=AU --design=latest
@Builder implement --spec=solar_design_v1.2
@SupportCopilot prepare --installation=commercial_rooftop
```

### Quality Gates
```
@SpecOverseer validate --all
@ComplianceBot audit --comprehensive
@Builder test --coverage=full
```

## Configuration Management

Each agent configuration includes:
- **Identity**: Name, role, version
- **Prompt**: Behavioral guidelines and expertise
- **Tools**: MCP tools and capabilities
- **Integration**: Connection points with other agents
- **Metrics**: Performance indicators and KPIs

## Security & Permissions

### Access Control
- **@SpecOverseer**: Read-only access, blocking authority
- **@SolarEngineer**: Domain data access, analysis tools
- **@ComplianceBot**: Regulatory database access, permit generation
- **@SupportCopilot**: Field documentation, visual analysis
- **@Builder**: Full development environment access

### Data Protection
- All agents follow 12-factor security principles
- PII encryption at rest
- Audit logging for all actions
- Role-based access control (RBAC)

## Monitoring & Analytics

### Performance Metrics
- Agent response times
- Task completion rates
- Quality scores
- User satisfaction ratings

### Usage Analytics
- Agent invocation frequency
- Workflow completion rates
- Error rates and resolution times
- Collaboration effectiveness

## Maintenance & Updates

### Version Control
- All agent configurations are version controlled
- Changes require @SpecOverseer validation
- Rollback capabilities for all updates

### Continuous Improvement
- Regular performance reviews
- User feedback integration
- Capability expansion based on needs
- Technology stack updates

---

**Last Updated**: 2025-01-25  
**Version**: 1.0.0  
**Maintainer**: NextGen Fusion Development Team