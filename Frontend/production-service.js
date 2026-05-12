const productionService = {
  // NOTE: Backend currently supports production registration by clerk role only.
  // Manager-side creation may require backend role adjustment.
  async registerProduction(productionData) {
    return apiRequest("/production/register", {
      method: "POST",
      body: productionData,
    });
  },

  async getProductions() {
    return apiRequest("/production/", { method: "GET" });
  },

  async searchProduction(name) {
    return apiRequest(`/production/${encodeURIComponent(name)}`, { method: "GET" });
  },

  async deleteProduction(productionId) {
    return apiRequest(`/production/${encodeURIComponent(productionId)}`, { method: "DELETE" });
  },
};

window.productionService = productionService;
