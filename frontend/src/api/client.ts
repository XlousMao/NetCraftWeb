import axios, { AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    let msg = '网络错误'
    if (status) {
      const detail = error.response?.data?.detail
      msg = typeof detail === 'string' ? detail : `服务器错误 (${status})`
    }
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

export default client
