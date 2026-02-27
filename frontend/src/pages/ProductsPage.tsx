import { useEffect, useState } from 'react'
import { Plus, Search, ShoppingBag, Edit2, Trash2 } from 'lucide-react'
import { productService } from '@/services/productService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Modal } from '@/components/common/Modal'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { formatCurrency } from '@/utils/formatters'
import type { Product, CreateProductRequest } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'

const STATUSES = ['', 'active', 'discontinued', 'new']

export function ProductsPage() {
  const { user } = useAuthStore()
  const canManage = can(user?.role, 'products.manage')

  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [editProduct, setEditProduct] = useState<Product | null>(null)
  const [form, setForm] = useState<Partial<CreateProductRequest>>({
    unit_of_measure: 'units',
    status: 'active',
    lead_time_days: 7,
    min_order_qty: 1,
  })
  const pageSize = 20

  const load = async () => {
    setLoading(true)
    try {
      const res = await productService.getProducts({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        search: search || undefined,
      })
      setProducts(res.items)
      setTotal(res.total)
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, statusFilter, search])

  const handleCreate = async () => {
    if (!form.sku || !form.name) {
      toast.error('SKU and name are required')
      return
    }
    try {
      if (editProduct) {
        await productService.updateProduct(editProduct.id, form)
        toast.success('Product updated')
      } else {
        await productService.createProduct(form as CreateProductRequest)
        toast.success('Product created')
      }
      setShowCreate(false)
      setEditProduct(null)
      setForm({ unit_of_measure: 'units', status: 'active', lead_time_days: 7, min_order_qty: 1 })
      load()
    } catch {
      // handled
    }
  }

  const handleEdit = (product: Product) => {
    setEditProduct(product)
    setForm({
      sku: product.sku,
      name: product.name,
      description: product.description,
      unit_of_measure: product.unit_of_measure,
      unit_cost: product.unit_cost,
      selling_price: product.selling_price,
      lead_time_days: product.lead_time_days,
      min_order_qty: product.min_order_qty,
      status: product.status,
    })
    setShowCreate(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this product?')) return
    try {
      await productService.deleteProduct(id)
      toast.success('Product deleted')
      load()
    } catch {
      // handled
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Products</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} products</p>
        </div>
        {canManage && (
          <Button icon={<Plus />} onClick={() => { setEditProduct(null); setShowCreate(true) }}>
            Add Product
          </Button>
        )}
      </div>

      <Card padding={false}>
        <div className="flex items-center gap-3 p-4">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search by name or SKU..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All Statuses'}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="p-4"><SkeletonTable rows={8} cols={7} /></div>
        ) : products.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <ShoppingBag className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No products found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['SKU', 'Name', 'Category', 'Unit Cost', 'Lead Time', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {products.map((product) => (
                  <tr key={product.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{product.sku}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{product.name}</p>
                      {product.product_family && (
                        <p className="text-xs text-gray-400">{product.product_family}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{product.category?.name ?? '—'}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {product.unit_cost != null ? formatCurrency(product.unit_cost) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{product.lead_time_days}d</td>
                    <td className="px-4 py-3"><StatusBadge status={product.status} size="sm" /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {canManage && (
                          <>
                            <button
                              onClick={() => handleEdit(product)}
                              className="p-1.5 rounded text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                              title="Edit"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => handleDelete(product.id)}
                              className="p-1.5 rounded text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {total > pageSize && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
            </p>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">
                Previous
              </button>
              <button disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">
                Next
              </button>
            </div>
          </div>
        )}
      </Card>

      <Modal isOpen={showCreate} onClose={() => { setShowCreate(false); setEditProduct(null) }}
        title={editProduct ? 'Edit Product' : 'Add Product'}
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => { setShowCreate(false); setEditProduct(null) }}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!canManage}>{editProduct ? 'Save Changes' : 'Create Product'}</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">SKU *</label>
              <input value={form.sku ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, sku: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., SKU-001" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Name *</label>
              <input value={form.name ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Product name" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Unit of Measure</label>
              <input value={form.unit_of_measure ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, unit_of_measure: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Unit Cost</label>
              <input type="number" step="0.01" value={form.unit_cost ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, unit_cost: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Selling Price</label>
              <input type="number" step="0.01" value={form.selling_price ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, selling_price: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Lead Time (days)</label>
              <input type="number" value={form.lead_time_days ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, lead_time_days: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Min Order Qty</label>
              <input type="number" value={form.min_order_qty ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, min_order_qty: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Status</label>
              <select value={form.status ?? 'active'}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as CreateProductRequest['status'] }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="active">Active</option>
                <option value="new">New</option>
                <option value="discontinued">Discontinued</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Description</label>
            <textarea value={form.description ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
          </div>
        </div>
      </Modal>
    </div>
  )
}
