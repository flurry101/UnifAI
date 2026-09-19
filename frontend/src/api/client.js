// API Client for UnifAI Backend

const getBaseUrl = () => {
  if (typeof window !== 'undefined') {
    return window.localStorage.getItem('UNIF_API_URL') || '';
  }
  return '';
};

export async function apiFetch(endpoint, options = {}) {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  
  const headers = {
    ...options.headers,
  };

  // Add auth token if available
  const token = localStorage.getItem('unifai_token');
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Handle JSON body
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errDetail = `HTTP ${res.status} ${res.statusText}`;
      try {
        const errorJson = await res.json();
        errDetail = errorJson.detail || JSON.stringify(errorJson);
      } catch (e) {
        // ignore parse error
      }
      const error = new Error(errDetail);
      error.status = res.status;
      throw error;
    }

    // Return JSON or text
    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await res.json();
    }
    return await res.text();
  } catch (err) {
    console.error(`API Error on ${url}:`, err);
    throw err;
  }
}

export async function checkBackendHealth() {
  try {
    const res = await fetch('/health');
    if (res.ok) {
      const data = await res.json();
      return { online: true, service: data.service || 'UnifAI Backend' };
    }
  } catch (e) {
    // If proxied fetch failed, try direct localhost:8000
    try {
      const res2 = await fetch('http://localhost:8000/health');
      if (res2.ok) {
        return { online: true, service: 'UnifAI Backend (Direct)' };
      }
    } catch (e2) {
      // offline
    }
  }
  return { online: false, error: 'Backend unreachable on :8000' };
}

