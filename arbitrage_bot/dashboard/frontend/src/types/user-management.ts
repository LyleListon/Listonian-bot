export interface UserRole {
  name: string;
  permissions: string[];
  description: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name?: string;
  picture?: string;
  provider: string;
  role: string;
  created_at: string;
  last_login: string;
  is_active: boolean;
  settings: Record<string, any>;
}

export interface UserUpdateRequest {
  name?: string;
  role?: string;
  is_active?: boolean;
  settings?: Record<string, any>;
}

export interface UserListResponse {
  users: UserProfile[];
  total: number;
}

export interface UserFilters {
  role?: string;
  search?: string;
  status?: 'active' | 'inactive';
}

export interface RoleListResponse {
  roles: UserRole[];
}

// API response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

// Default roles and their permissions
export const DEFAULT_ROLES: Record<string, string[]> = {
  admin: [
    'manage_users',
    'manage_roles',
    'view_all_data',
    'manage_system',
  ],
  manager: [
    'view_all_data',
    'manage_trading',
    'view_analytics',
  ],
  viewer: [
    'view_basic_data',
    'view_own_profile',
  ],
};

// Permission descriptions for UI
export const PERMISSION_DESCRIPTIONS: Record<string, string> = {
  manage_users: 'Create, update, and delete user accounts',
  manage_roles: 'Manage user roles and permissions',
  view_all_data: 'View all system data and analytics',
  manage_system: 'Configure system settings and features',
  manage_trading: 'Manage trading strategies and execution',
  view_analytics: 'View detailed analytics and reports',
  view_basic_data: 'View basic system information',
  view_own_profile: 'View and edit own user profile',
};