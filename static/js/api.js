// SmartPlate AI - Centralized API Client
const API = {
  async get(url) {
    try {
      const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
      const data = await resp.json();
      return data;
    } catch (err) {
      console.error('API GET Error:', err);
      return { success: False, error: 'Network communication error.' };
    }
  },

  async post(url, body = {}) {
    try {
      const isFormData = body instanceof FormData;
      const options = {
        method: 'POST',
        headers: isFormData ? {} : { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: isFormData ? body : JSON.stringify(body)
      };
      const resp = await fetch(url, options);
      const data = await resp.json();
      return data;
    } catch (err) {
      console.error('API POST Error:', err);
      return { success: false, error: 'Network communication error.' };
    }
  },

  async put(url, body = {}) {
    try {
      const resp = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await resp.json();
      return data;
    } catch (err) {
      console.error('API PUT Error:', err);
      return { success: false, error: 'Network communication error.' };
    }
  }
};
