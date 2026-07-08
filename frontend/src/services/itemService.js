const API_BASE_URL = '/api/items'

const itemService = {
    async fetchItems(params = {}) {
        // Placeholder: fetch item list from the API
        return Promise.resolve({ data: [] })
    },

    async fetchItemById(id) {
        // Placeholder: fetch a single item by id
        return Promise.resolve({ data: null })
    },
}

export default itemService