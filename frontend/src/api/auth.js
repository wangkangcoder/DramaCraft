import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const authClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const loginAPI = async (payload) => authClient.post('/auth/login', payload)

export const registerAPI = async (payload) => authClient.post('/auth/register', payload)
