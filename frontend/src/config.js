// Environment configuration for frontend
// This file handles both development and production API endpoints

// Get API URL from environment variable or use defaults
const getApiBaseUrl = () => {
  // Check for Vite environment variable first
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  
  // Fallback to React environment variable
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL
  }
  
  // Default based on environment
  const isDev = import.meta.env.DEV || process.env.NODE_ENV === 'development'
  return isDev ? 'http://localhost:8000' : 'https://2i7mq7kfxp.us-east-1.awsapprunner.com'
}

const config = {
  API_BASE_URL: getApiBaseUrl(),
  ENVIRONMENT: import.meta.env.DEV ? 'development' : 'production'
}

// Export configuration
export default config

// Helper function to get full API URL
export const getApiUrl = (endpoint) => {
  const baseUrl = config.API_BASE_URL
  // Remove leading slash from endpoint if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
  return `${baseUrl}/${cleanEndpoint}`
}

// Helper function to check if we're in development
export const isDevelopment = () => config.ENVIRONMENT === 'development'

// Helper function to check if we're in production
export const isProduction = () => config.ENVIRONMENT === 'production'

// Debug function to log current configuration
export const logConfig = () => {
  if (isDevelopment()) {
    console.log('🔧 Frontend Configuration:', {
      API_BASE_URL: config.API_BASE_URL,
      ENVIRONMENT: config.ENVIRONMENT,
      VITE_API_URL: import.meta.env.VITE_API_URL,
      NODE_ENV: process.env.NODE_ENV
    })
  }
}
