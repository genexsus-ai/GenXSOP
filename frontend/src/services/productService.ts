import api from './api'
import type { Product, Category, CreateProductRequest, PaginatedResponse } from '@/types'

export const productService = {
  async getProducts(params?: { page?: number; page_size?: number; status?: string; category_id?: number; search?: string }): Promise<PaginatedResponse<Product>> {
    const res = await api.get<PaginatedResponse<Product>>('/products', { params })
    return res.data
  },

  async getProduct(id: number): Promise<Product> {
    const res = await api.get<Product>(`/products/${id}`)
    return res.data
  },

  async createProduct(data: CreateProductRequest): Promise<Product> {
    const res = await api.post<Product>('/products', data)
    return res.data
  },

  async updateProduct(id: number, data: Partial<CreateProductRequest>): Promise<Product> {
    const res = await api.put<Product>(`/products/${id}`, data)
    return res.data
  },

  async deleteProduct(id: number): Promise<void> {
    await api.delete(`/products/${id}`)
  },

  async getCategories(): Promise<Category[]> {
    const res = await api.get<Category[]>('/categories')
    return res.data
  },

  async createCategory(data: { name: string; parent_id?: number; description?: string }): Promise<Category> {
    const res = await api.post<Category>('/categories', data)
    return res.data
  },
}
