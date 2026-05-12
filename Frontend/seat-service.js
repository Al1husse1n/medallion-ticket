const seatService = {
  async initializeSeats() {
    return apiRequest("/seat/initialize", { method: "POST" });
  },

  async getSeats() {
    return apiRequest("/seat/", { method: "GET" });
  },

  async getSeatsByCategory(category) {
    return apiRequest(`/seat/by-category/${encodeURIComponent(category)}`, { method: "GET" });
  },

  async getAvailableSeats() {
    return apiRequest("/seat/available", { method: "GET" });
  },

  async deleteSeat(seatId) {
    return apiRequest(`/seat/${encodeURIComponent(seatId)}`, { method: "DELETE" });
  },
};

window.seatService = seatService;
