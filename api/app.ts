import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import authRoutes from './routes/auth.js'
import adminRoutes from './routes/admin.js'
import enterpriseRoutes from './routes/enterprise.js'
import mfaRoutes from './routes/mfa.js'
import auth0Middleware from './middleware/auth0.js'

// Load environment variables
dotenv.config()

const app = express()

// Middleware
app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? process.env.FRONTEND_URL || 'https://your-domain.com'
    : ['http://localhost:3000', 'http://localhost:5173'],
  credentials: true
}))
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

// Auth0 middleware will initialize itself when first used

// Routes
app.use('/api/auth', authRoutes)
app.use('/api/admin', adminRoutes)
app.use('/api/enterprise', enterpriseRoutes)
app.use('/api/mfa', mfaRoutes)

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    auth0: {
      configured: !!(process.env.AUTH0_DOMAIN && process.env.AUTH0_API_AUDIENCE)
    }
  })
})

// Protected route example
app.get('/api/protected', auth0Middleware.authenticate, (req: any, res) => {
  res.json({
    message: 'This is a protected route',
    user: req.user
  })
})

// Error handling middleware
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Error:', err.message)
  
  if (err.name === 'UnauthorizedError') {
    res.status(401).json({ 
      error: 'Unauthorized',
      message: err.message 
    })
    return
  }
  
  if (err.name === 'TokenExpiredError') {
    res.status(401).json({ 
      error: 'Token expired',
      message: 'Please log in again' 
    })
    return
  }
  
  res.status(500).json({ 
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  })
})

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' })
})

export default app
