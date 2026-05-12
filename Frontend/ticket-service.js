const ticketService = {
  async createTicket(ticketData) {
    return apiRequest("/ticket/create", {
      method: "POST",
      body: ticketData,
    });
  },

  async getTickets() {
    return apiRequest("/ticket/", { method: "GET" });
  },

  async getTicketById(ticketId) {
    return apiRequest(`/ticket/${encodeURIComponent(ticketId)}`, { method: "GET" });
  },

  async getTicketsByPatron(patronId) {
    return apiRequest(`/ticket/by-patron/${encodeURIComponent(patronId)}`, { method: "GET" });
  },

  async getTicketsByPerformance(performanceId) {
    return apiRequest(`/ticket/by-performance/${encodeURIComponent(performanceId)}`, { method: "GET" });
  },

  async cancelTicket(ticketId) {
    return apiRequest(`/ticket/${encodeURIComponent(ticketId)}/cancel`, { method: "POST" });
  },

  async deleteTicket(ticketId) {
    return apiRequest(`/ticket/${encodeURIComponent(ticketId)}`, { method: "DELETE" });
  },
};

window.ticketService = ticketService;
