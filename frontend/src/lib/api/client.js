/**
 * NetInsight API client.
 * Wraps fetch() with authentication and base URL management.
 */

const BASE_URL = '/api/v1';

class ApiClient {
  constructor() {
    this.token = null;
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('netinsight_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('netinsight_token');
  }

  loadToken() {
    this.token = localStorage.getItem('netinsight_token');
    return this.token;
  }

  getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
  }

  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const cookieToken = this.getCookie('access_token');
    const token = cookieToken || this.token || this.loadToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async request(method, path, body = null) {
    const url = `${BASE_URL}${path}`;
    const options = {
      method,
      headers: this.getHeaders(),
    };
    if (body !== null) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (response.status === 204) {
      return null;
    }

    const data = await response.json();

    if (!response.ok) {
      let msg = 'API request failed';
      if (typeof data.detail === 'string') {
        msg = data.detail;
      } else if (Array.isArray(data.detail)) {
        msg = data.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
      } else if (data.detail) {
        msg = JSON.stringify(data.detail);
      }
      const err = new Error(msg);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  }

  get(path) {
    return this.request('GET', path);
  }

  post(path, body) {
    return this.request('POST', path, body);
  }

  delete(path) {
    return this.request('DELETE', path);
  }

  // === Auth ===
  login(email, password) {
    return this.post('/auth/login', { email, password });
  }

  register(email, password, fullName = null) {
    return this.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
  }

  // === Dashboard ===
  getStats() {
    return this.get('/dashboard/stats');
  }

  // === Campaigns ===
  getCampaigns(statusFilter = null) {
    const params = statusFilter ? `?status=${statusFilter}` : '';
    return this.get(`/campaigns/${params}`);
  }

  getCampaign(id) {
    return this.get(`/campaigns/${id}`);
  }

  createCampaign(data) {
    return this.post('/campaigns/', data);
  }

  deleteCampaign(id) {
    return this.delete(`/campaigns/${id}`);
  }

  // === Hosts ===
  getHosts(campaignId = null) {
    const params = campaignId ? `?campaign_id=${campaignId}` : '';
    return this.get(`/hosts/${params}`);
  }

  getHost(id) {
    return this.get(`/hosts/${id}`);
  }

  getHostPorts(hostId) {
    return this.get(`/hosts/${hostId}/ports`);
  }

  // === Scan ===
  triggerScan(campaignId) {
    return this.post(`/campaigns/${campaignId}/scan`);
  }

  // === Reports ===
  triggerReport(campaignId) {
    return this.post(`/campaigns/${campaignId}/report`);
  }

  getCampaignReport(campaignId) {
    return this.get(`/campaigns/${campaignId}/report`);
  }

  getReportDownloadUrl(reportId) {
    return `${BASE_URL}/reports/${reportId}/download`;
  }

  async downloadReport(reportId, filename = 'report.pdf') {
    const url = this.getReportDownloadUrl(reportId);
    const response = await fetch(url, { headers: this.getHeaders() });
    if (!response.ok) throw new Error('Download failed');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }

  // === Vulnerabilities ===
  getVulnerabilities(hostId = null, severity = null) {
    const params = new URLSearchParams();
    if (hostId) params.set('host_id', hostId);
    if (severity) params.set('severity', severity);
    const qs = params.toString();
    return this.get(`/vulnerabilities/${qs ? '?' + qs : ''}`);
  }

  getVulnerability(id) {
    return this.get(`/vulnerabilities/${id}`);
  }

  getHostVulnerabilities(hostId) {
    return this.get(`/hosts/${hostId}/vulnerabilities`);
  }

  enrichHost(hostId) {
    return this.post(`/hosts/${hostId}/enrich`);
  }

  // === Sqlmap ===
  getSqlmapScans(statusFilter = null) {
    const params = statusFilter ? `?status=${statusFilter}` : '';
    return this.get(`/sqlmap/${params}`);
  }

  getSqlmapScan(id) {
    return this.get(`/sqlmap/${id}`);
  }

  createSqlmapScan(data) {
    return this.post('/sqlmap/', data);
  }

  deleteSqlmapScan(id) {
    return this.delete(`/sqlmap/${id}`);
  }

  triggerSqlmapScan(scanId) {
    return this.post(`/sqlmap/${scanId}/scan`);
  }

  exportSqlmapScan(scanId, format = 'json') {
    return this.get(`/sqlmap/${scanId}/export?format=${format}`);
  }

  getSqlmapExportUrl(scanId, format = 'json') {
    return `${BASE_URL}/sqlmap/${scanId}/export?format=${format}`;
  }

  async downloadSqlmapExport(scanId, format = 'json') {
    const url = this.getSqlmapExportUrl(scanId, format);
    const response = await fetch(url, { headers: this.getHeaders() });
    if (!response.ok) throw new Error('Export failed');
    const blob = await response.blob();
    const ext = format === 'csv' ? 'csv' : 'json';
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `sqlmap_${scanId}.${ext}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }

  // === Admin / Users ===
  getUsers(roleFilter = null) {
    const params = roleFilter ? `?role=${roleFilter}` : '';
    return this.get(`/admin/users/${params}`);
  }

  createUser(email, password, fullName = null, role = 'analyst') {
    return this.post(`/admin/users/?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}&full_name=${encodeURIComponent(fullName || '')}&role=${role}`);
  }

  updateUserRole(userId, role) {
    return this.put(`/admin/users/${userId}/role?role=${role}`);
  }

  toggleUserActive(userId) {
    return this.put(`/admin/users/${userId}/toggle-active`);
  }

  deleteUser(userId) {
    return this.delete(`/admin/users/${userId}`);
  }

  put(path) {
    return this.request('PUT', path);
  }

  // === MITRE ATT&CK ===
  getMitreTactics() {
    return this.get('/mitre/tactics');
  }

  getMitreTechniques(tactic = null, search = null) {
    const params = [];
    if (tactic) params.push(`tactic=${encodeURIComponent(tactic)}`);
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    const qs = params.length ? '?' + params.join('&') : '';
    return this.get(`/mitre/techniques${qs}`);
  }

  getMitreTechnique(id) {
    return this.get(`/mitre/techniques/${id}`);
  }

  getMitreMappings(techniqueId = null) {
    const qs = techniqueId ? `?technique_id=${techniqueId}` : '';
    return this.get(`/mitre/mappings${qs}`);
  }

  getMitreStats() {
    return this.get('/mitre/stats');
  }

  // === Audit ===
  getAuditLogs(action = null, userEmail = null, limit = 100) {
    const params = [];
    if (action) params.push(`action=${encodeURIComponent(action)}`);
    if (userEmail) params.push(`user_email=${encodeURIComponent(userEmail)}`);
    params.push(`limit=${limit}`);
    return this.get(`/audit/?${params.join('&')}`);
  }

  // === Nikto ===
  getNiktoScans(statusFilter = null) {
    const params = statusFilter ? `?status=${statusFilter}` : '';
    return this.get(`/nikto/${params}`);
  }

  getNiktoScan(id) {
    return this.get(`/nikto/${id}`);
  }

  createNiktoScan(data) {
    return this.post('/nikto/', data);
  }

  deleteNiktoScan(id) {
    return this.delete(`/nikto/${id}`);
  }

  triggerNiktoScan(scanId) {
    return this.post(`/nikto/${scanId}/scan`);
  }

  // === Banners ===
  getHostBanners(hostId) {
    return this.get(`/banners/host/${hostId}`);
  }

  grabBanners(hostId) {
    return this.post(`/banners/host/${hostId}/grab`);
  }
}

export const api = new ApiClient();
