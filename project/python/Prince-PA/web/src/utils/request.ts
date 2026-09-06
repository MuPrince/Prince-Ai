import axios, { type AxiosRequestConfig } from 'axios'

const instance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000
})

instance.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error?.response?.data || error)
)

const request = {
  get: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    (await instance.get<T>(url, config)).data,
  post: async <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    (await instance.post<T>(url, data, config)).data,
  put: async <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    (await instance.put<T>(url, data, config)).data,
  patch: async <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    (await instance.patch<T>(url, data, config)).data
}

export default request
