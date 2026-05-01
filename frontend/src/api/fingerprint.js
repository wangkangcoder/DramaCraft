import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const LONG_RUNNING_TIMEOUT = 900000

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: LONG_RUNNING_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const analyzeNarrativeFingerprint = async (payload) => {
  return await apiClient.post('/fingerprint/analyze', payload, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}
