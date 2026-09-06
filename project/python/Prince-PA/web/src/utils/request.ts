import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error?.response?.data || error)
)

export default request
