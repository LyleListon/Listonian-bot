import React, { useState, useEffect, ChangeEvent, MouseEvent } from 'react';
import type { ReactElement } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Avatar,
  Tooltip,
  Alert,
  SelectChangeEvent,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Check as CheckIcon,
  Block as BlockIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { useAuth } from '../providers/AuthProvider';
import {
  UserProfile,
  UserRole,
  UserUpdateRequest,
  UserFilters,
  DEFAULT_ROLES,
  PERMISSION_DESCRIPTIONS,
} from '../types/user-management';

const UserManagement = (): ReactElement => {
  const { user } = useAuth();
  const { enqueueSnackbar } = useSnackbar();
  
  // State
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [roles, setRoles] = useState<UserRole[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  // Filters
  const [filters, setFilters] = useState<UserFilters>({});
  
  // Load users and roles
  useEffect(() => {
    const loadData = async (): Promise<void> => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch users
        const usersResponse = await fetch('/api/users', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        if (!usersResponse.ok) throw new Error('Failed to fetch users');
        const usersData = await usersResponse.json() as UserProfile[];
        setUsers(usersData);
        
        // Fetch roles
        const rolesResponse = await fetch('/api/roles', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        if (!rolesResponse.ok) throw new Error('Failed to fetch roles');
        const rolesData = await rolesResponse.json() as UserRole[];
        setRoles(rolesData);
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        enqueueSnackbar('Failed to load user data', { variant: 'error' });
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [enqueueSnackbar]);
  
  // Handle user update
  const handleUserUpdate = async (userId: string, data: UserUpdateRequest): Promise<void> => {
    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) throw new Error('Failed to update user');
      
      const updatedUser = await response.json() as UserProfile;
      setUsers(users.map((u: UserProfile) => u.id === userId ? updatedUser : u));
      enqueueSnackbar('User updated successfully', { variant: 'success' });
      setEditDialogOpen(false);
      
    } catch (err) {
      enqueueSnackbar(
        err instanceof Error ? err.message : 'Failed to update user',
        { variant: 'error' }
      );
    }
  };
  
  // Filter users
  const filteredUsers = users.filter((user: UserProfile) => {
    if (filters.role && user.role !== filters.role) return false;
    if (filters.status === 'active' && !user.is_active) return false;
    if (filters.status === 'inactive' && user.is_active) return false;
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      return (
        user.name?.toLowerCase().includes(searchTerm) ||
        user.email.toLowerCase().includes(searchTerm)
      );
    }
    return true;
  });
  
  // Render user edit dialog
  const renderEditDialog = (): ReactElement => (
    <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}>
      <DialogTitle>
        Edit User: {selectedUser?.name || selectedUser?.email}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Name"
            defaultValue={selectedUser?.name}
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              if (selectedUser) {
                handleUserUpdate(selectedUser.id, { name: e.target.value });
              }
            }}
          />
          
          <FormControl>
            <InputLabel>Role</InputLabel>
            <Select
              value={selectedUser?.role || ''}
              onChange={(e: SelectChangeEvent<string>) => {
                if (selectedUser) {
                  handleUserUpdate(selectedUser.id, { role: e.target.value });
                }
              }}
            >
              {roles.map((role: UserRole) => (
                <MenuItem key={role.name} value={role.name}>
                  {role.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl>
            <InputLabel>Status</InputLabel>
            <Select
              value={selectedUser?.is_active ? 'active' : 'inactive'}
              onChange={(e: SelectChangeEvent<string>) => {
                if (selectedUser) {
                  handleUserUpdate(selectedUser.id, {
                    is_active: e.target.value === 'active'
                  });
                }
              }}
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="inactive">Inactive</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
        <Button
          onClick={() => {
            if (selectedUser) {
              handleUserUpdate(selectedUser.id, {
                name: selectedUser.name,
                role: selectedUser.role,
                is_active: selectedUser.is_active,
              });
            }
          }}
          color="primary"
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
  
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        User Management
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            label="Search"
            size="small"
            InputProps={{
              startAdornment: <SearchIcon />,
            }}
            onChange={(e: ChangeEvent<HTMLInputElement>) => 
              setFilters({ ...filters, search: e.target.value })
            }
          />
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Role</InputLabel>
            <Select
              value={filters.role || ''}
              onChange={(e: SelectChangeEvent<string>) => 
                setFilters({ ...filters, role: e.target.value })
              }
            >
              <MenuItem value="">All</MenuItem>
              {roles.map((role: UserRole) => (
                <MenuItem key={role.name} value={role.name}>
                  {role.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filters.status || ''}
              onChange={(e: SelectChangeEvent<string>) => setFilters({
                ...filters,
                status: e.target.value as 'active' | 'inactive' | undefined
              })}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="inactive">Inactive</MenuItem>
            </Select>
          </FormControl>
          
          <Button
            startIcon={<RefreshIcon />}
            onClick={() => setFilters({})}
          >
            Reset
          </Button>
        </Box>
      </Paper>
      
      {/* User Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>User</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Login</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredUsers
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((user: UserProfile) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Avatar src={user.picture} alt={user.name}>
                        {user.name?.[0] || user.email[0]}
                      </Avatar>
                      <Typography>{user.name || user.email}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Chip
                      label={user.role}
                      color={user.role === 'admin' ? 'error' : 'primary'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={user.is_active ? <CheckIcon /> : <BlockIcon />}
                      label={user.is_active ? 'Active' : 'Inactive'}
                      color={user.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {new Date(user.last_login).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Edit user">
                      <IconButton
                        onClick={() => {
                          setSelectedUser(user);
                          setEditDialogOpen(true);
                        }}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
        
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={filteredUsers.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_: MouseEvent<HTMLButtonElement> | null, newPage: number) => setPage(newPage)}
          onRowsPerPageChange={(e: ChangeEvent<HTMLInputElement>) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
        />
      </TableContainer>
      
      {renderEditDialog()}
    </Box>
  );
};

export default UserManagement;