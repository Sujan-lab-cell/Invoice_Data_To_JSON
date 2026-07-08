const API_BASE_URL = '/api/suppliers'

const supplierService = {
    async fetchSuppliers(params = {}) {
        // Placeholder: fetch supplier list from the API
        return Promise.resolve({ data: [] })
    },

    async fetchSupplierById(id) {
        // Placeholder: fetch a single supplier by id
        return Promise.resolve({ data: null })
    },
}

export default supplierService