import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { isAdminRole } from '@/features/auth/roles'
import { listPlants, type Plant } from '@/features/admin/api/plants'
import { listUserPlantAccess } from '@/features/admin/api/users'

/** Plants the signed-in user may see: all of them for `admin`, otherwise
 * only the ones they've been granted access to via user_plant_access. */
export function useScopedPlants(): { plants: Plant[]; isAdmin: boolean; isLoading: boolean } {
  const { user } = useAuth()
  const admin = isAdminRole(user?.role)

  const allPlants = useQuery({
    queryKey: ['admin', 'plants'],
    queryFn: listPlants,
    enabled: admin,
  })
  const ownPlants = useQuery({
    queryKey: ['admin', 'users', user?.id, 'plant-access'],
    queryFn: () => listUserPlantAccess(user!.id),
    enabled: Boolean(user) && !admin,
  })

  return {
    plants: admin ? (allPlants.data ?? []) : (ownPlants.data ?? []),
    isAdmin: admin,
    isLoading: admin ? allPlants.isLoading : ownPlants.isLoading,
  }
}
