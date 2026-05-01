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

export const syncNarrativeGraph = async (content) => {
  return await apiClient.post('/narrative/sync_graph', { content }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}

export const generateNextAct = async (content, outline = '', characters = '', idea = '', scriptFormat = '') => {
  return await apiClient.post('/narrative/generate_act', {
    content,
    outline,
    characters,
    idea,
    script_format: scriptFormat,
  }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}

export const reviewCurrentAct = async (content, outline = '', characters = '', idea = '', scriptFormat = '') => {
  return await apiClient.post('/narrative/review_current_act', {
    content,
    outline,
    characters,
    idea,
    script_format: scriptFormat,
  }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}

export const reviseCurrentAct = async (content, outline = '', characters = '', idea = '', analysis = null, scriptFormat = '') => {
  return await apiClient.post('/narrative/revise_current_act', {
    content,
    outline,
    characters,
    idea,
    analysis,
    script_format: scriptFormat,
  }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}
