const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Health check endpoint
 */
export const healthCheck = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = await response.json();
    return data;
  } catch (error) {
    throw new Error('Backend server is not reachable');
  }
};

/**
 * Onboard a new client
 * @param {Object} formData - Client form data
 * @param {Array} images - Array of image files
 * @param {Array} videos - Array of video files
 */
export const onboardClient = async (formData, images = [], videos = []) => {
  try {
    const formDataToSend = new FormData();

    // Append all form fields
    Object.keys(formData).forEach(key => {
      if (key === 'primary_channels') {
        // Join channels array into comma-separated string
        formDataToSend.append(key, formData[key].join(', '));
      } else if (key === 'generate_images') {
        // Convert boolean to string for form data
        formDataToSend.append(key, formData[key] ? 'true' : 'false');
      } else {
        formDataToSend.append(key, formData[key] || '');
      }
    });

    // Append image files
    images.forEach(image => {
      formDataToSend.append('images', image);
    });

    // Append video files
    videos.forEach(video => {
      formDataToSend.append('videos', video);
    });

    const response = await fetch(`${API_BASE_URL}/api/client/onboard`, {
      method: 'POST',
      body: formDataToSend
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.message || 'Failed to onboard client');
    }

    return result;
  } catch (error) {
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      throw new Error('Cannot connect to backend server. Make sure the server is running on http://localhost:8000');
    }
    throw error;
  }
};

/**
 * Get all clients
 */
export const getClients = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/clients`);
    const data = await response.json();
    return data;
  } catch (error) {
    throw new Error('Failed to fetch clients');
  }
};

/**
 * Get a specific client by ID
 */
export const getClient = async (clientId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/client/${clientId}`);
    const data = await response.json();
    return data;
  } catch (error) {
    throw new Error('Failed to fetch client');
  }
};

/**
 * Get pending content for approval
 */
export const getPendingContent = async (clientId = 'all') => {
  try {
    const url = clientId === 'all' 
      ? `${API_BASE_URL}/api/content/pending`
      : `${API_BASE_URL}/api/content/pending?client_id=${clientId}`;
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    throw new Error('Failed to fetch pending content');
  }
};

/**
 * Approve content
 */
export const approveContent = async (contentId, platform = null, credentials = null) => {
  try {
    const requestBody = {};
    if (platform) {
      requestBody.platform = platform;
    }
    if (credentials) {
      requestBody.credentials = credentials;
    }
    
    console.log('Approving content:', { contentId, platform, hasCredentials: !!credentials });
    
    const response = await fetch(`${API_BASE_URL}/api/content/${contentId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      console.error('Approve content error:', data);
      throw new Error(data.message || data.error || `HTTP ${response.status}: Failed to approve content`);
    }
    
    if (!data.success) {
      console.error('Approve content failed:', data);
      throw new Error(data.message || 'Failed to approve content');
    }
    
    console.log('Content approved successfully:', data);
    return data;
  } catch (error) {
    console.error('Error in approveContent:', error);
    throw error;
  }
};

/**
 * Edit content
 */
export const editContent = async (contentId, newContent) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/content/${contentId}/edit`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content: newContent })
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message || 'Failed to edit content');
    }
    return data;
  } catch (error) {
    throw new Error('Failed to edit content');
  }
};

/**
 * Delete content
 */
export const deleteContent = async (contentId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/content/${contentId}`, {
      method: 'DELETE'
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message || 'Failed to delete content');
    }
    return data;
  } catch (error) {
    throw new Error('Failed to delete content');
  }
};

/**
 * Regenerate content
 */
export const regenerateContent = async (contentId, platform, contentType, improvementFocus = null) => {
  try {
    const requestBody = { 
      platform, 
      content_type: contentType 
    };
    
    if (improvementFocus) {
      requestBody.improvement_focus = improvementFocus;
    }
    
    const response = await fetch(`${API_BASE_URL}/api/content/${contentId}/regenerate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message || 'Failed to regenerate content');
    }
    return data;
  } catch (error) {
    throw new Error('Failed to regenerate content');
  }
};

/**
 * Get analytics data
 */
export const getAnalytics = async (timeRange = '7d') => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/analytics?time_range=${timeRange}`);
    const data = await response.json();
    return data;
  } catch (error) {
    throw new Error('Failed to fetch analytics');
  }
};

/**
 * Get dashboard stats
 */
export const getDashboardStats = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dashboard/stats`);
    const data = await response.json();
    return data;
  } catch (error) {
    throw new Error('Failed to fetch dashboard stats');
  }
};

/**
 * Get campaigns
 */
export const getCampaigns = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/campaigns`);
    const data = await response.json();
    return data;
  } catch (error) {
    throw new Error('Failed to fetch campaigns');
  }
};

/**
 * Create campaign
 */
export const createCampaign = async (campaignData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/campaigns`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(campaignData)
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message || 'Failed to create campaign');
    }
    return data;
  } catch (error) {
    throw new Error('Failed to create campaign');
  }
};

/**
 * Update campaign
 */
export const updateCampaign = async (campaignId, campaignData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/campaigns/${campaignId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(campaignData)
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message || 'Failed to update campaign');
    }
    return data;
  } catch (error) {
    throw new Error('Failed to update campaign');
  }
};

/**
 * Delete campaign
 */
export const deleteCampaign = async (campaignId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/campaigns/${campaignId}`, {
      method: 'DELETE'
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message || 'Failed to delete campaign');
    }
    return data;
  } catch (error) {
    throw new Error('Failed to delete campaign');
  }
};
