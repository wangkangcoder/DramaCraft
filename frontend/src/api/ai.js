
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const LONG_RUNNING_TIMEOUT = 900000

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: LONG_RUNNING_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Generate Character Profiles
export const generateCharacters = async (idea, scriptFormat) => {
  return await apiClient.post('/ai/narrative/characters', { idea, script_format: scriptFormat }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}

// Generate Outline
export const generateOutline = async (idea, characters, scriptFormat) => {
  return await apiClient.post('/ai/narrative/outline', { idea, characters, script_format: scriptFormat }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}

// Generate Script
export const generatePipelineScript = async (idea, characters, outline, scriptFormat) => {
  return await apiClient.post('/ai/narrative/script', {
    idea,
    characters,
    outline,
    script_format: scriptFormat,
  }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}

export const generateSeriesNextEpisodePrefill = async (currentEpisode) => {
  return await apiClient.post('/ai/narrative/series-next-episode-prefill', {
    current_episode: currentEpisode,
    script_format: 'series',
  }, {
    timeout: LONG_RUNNING_TIMEOUT,
  })
}

export const getRuntimeAISettings = async () => {
  return await apiClient.get('/ai/runtime-settings')
}

export const saveRuntimeAISettings = async (payload) => {
  return await apiClient.post('/ai/runtime-settings', payload)
}
