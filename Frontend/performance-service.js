const performanceService = {
  async registerPerformance(performanceData) {
    return apiRequest("/performance/register", {
      method: "POST",
      body: performanceData,
    });
  },

  async getPerformancesByDate(date) {
    return apiRequest(`/performance/performance_date?performance_date=${encodeURIComponent(date)}`, { method: "GET" });
  },

  async getUpcomingPerformances() {
    return apiRequest(`/performance?future=true`, { method: "GET" });
  },

  async deletePerformance(performanceId) {
    return apiRequest(`/performance/${encodeURIComponent(performanceId)}`, { method: "DELETE" });
  },
};

window.performanceService = performanceService;
