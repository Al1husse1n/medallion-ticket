const patronService = {
  async registerPatron(patronData) {
    return apiRequest("/patron/register", {
      method: "POST",
      body: patronData,
    });
  },

  async getPatrons(cursor = null) {
    const query = [];
    if (cursor !== null) {
      query.push(`cursor=${encodeURIComponent(cursor)}`);
    }
    query.push(`limit=20`);
    const path = `/patron/?${query.join("&")}`;
    return apiRequest(path, { method: "GET" });
  },

  async getPatronByEmail(email) {
    return apiRequest(`/patron/${encodeURIComponent(email)}`, { method: "GET" });
  },

  async deletePatron(email) {
    return apiRequest(`/patron/${encodeURIComponent(email)}`, { method: "DELETE" });
  },

  // Future endpoint note: client-side edit UI exists, but backend needs a patron update endpoint.
  async updatePatron(patronData) {
    showToast('Update endpoint not available yet.', 'info');
    return { success: false, error: 'Patron update endpoint not implemented' };
  },
};

window.patronService = patronService;
