export const routes = {
  login: '/pages/login/index',
  home: '/pages/home/index',
  campuses: '/pages/campuses/index',
  labs: '/pages/labs/index',
  labDetail: '/pages/lab-detail/index',
  schedule: '/pages/schedule/index',
  reserve: '/pages/reserve/index',
  assetRequests: '/pages/asset-requests/index',
  dailyReport: '/pages/daily-report/index',
  notifications: '/pages/notifications/index',
  myReservations: '/pages/my-reservations/index',
  reservationDetail: '/pages/reservation-detail/index',
  profile: '/pages/profile/index',
  agent: '/pages/agent/index',
  adminCampuses: '/pages/admin-campuses/index',
  adminLabs: '/pages/admin-labs/index',
  adminEquipment: '/pages/admin-equipment/index',
  adminApprovals: '/pages/admin-approvals/index',
  adminAssetRequests: '/pages/admin-asset-requests/index',
  adminDailyReports: '/pages/admin-daily-reports/index',
  adminUsers: '/pages/admin-users/index',
  adminProfile: '/pages/admin-profile/index',
  adminLogs: '/pages/admin-logs/index',
  statistics: '/pages/statistics/index'
}

export const userTabs = [
  { key: 'home', title: '首页', path: routes.home, desc: '预约入口与资源推荐' },
  { key: 'labs', title: '实验室', path: routes.labs, desc: '按条件检索实验室' },
  { key: 'reservations', title: '我的预约', path: routes.myReservations, desc: '跟踪预约状态' },
  { key: 'profile', title: '我的', path: routes.profile, desc: '账户信息与常用入口' }
]

export const userTopNav = [
  { key: 'home', title: '首页', path: routes.home },
  { key: 'campuses', title: '校区资源', path: routes.campuses },
  { key: 'labs', title: '实验室预约', path: routes.labs },
  { key: 'reservations', title: '我的预约', path: routes.myReservations },
  { key: 'agent', title: 'AI 助手', path: routes.agent },
  { key: 'profile', title: '个人中心', path: routes.profile }
]

export const userQuickEntries = [
  { title: '校区列表', desc: '查看校区实验室分布', path: routes.campuses, layout: 'card' },
  { title: '实验室列表', desc: '按校区和条件筛选实验室', path: routes.labs, layout: 'filter-list' },
  { title: '我的预约', desc: '集中查看预约记录', path: routes.myReservations, layout: 'table-mix' },
  { title: '个人中心', desc: '查看个人与角色信息', path: routes.profile, layout: 'card' }
]

export const adminMenus = [
  {
    key: 'campuses',
    title: '校区管理',
    desc: '维护校区信息与状态',
    path: routes.adminCampuses,
    group: '资源管理'
  },
  {
    key: 'labs',
    title: '实验室管理',
    desc: '维护实验室与开放时段',
    path: routes.adminLabs,
    group: '资源管理'
  },
  {
    key: 'equipment',
    title: '设备管理',
    desc: '维护设备状态与归属',
    path: routes.adminEquipment,
    group: '资源管理'
  },
  {
    key: 'approvals',
    title: '预约审批',
    desc: '处理预约审批',
    path: routes.adminApprovals,
    group: '预约管理'
  },
  {
    key: 'assetRequests',
    title: '资产审批',
    desc: '处理教师资产申报与预算流转',
    path: routes.adminAssetRequests,
    group: '预约管理'
  },
  {
    key: 'dailyReports',
    title: '日报审核',
    desc: '审核学生/教师提交的实验室日报',
    path: routes.adminDailyReports,
    group: '预约管理'
  },
  {
    key: 'users',
    title: '用户管理',
    desc: '维护账号与角色',
    path: routes.adminUsers,
    group: '权限管理'
  },
  {
    key: 'logs',
    title: '日志审计',
    desc: '查看关键业务操作日志',
    path: routes.adminLogs,
    group: '分析看板'
  },
  {
    key: 'statistics',
    title: '统计分析',
    desc: '查看运营统计',
    path: routes.statistics,
    group: '分析看板'
  }
]

export const adminShortcutEntries = [
  { title: '处理审批', path: routes.adminApprovals, variant: 'primary' },
  { title: '维护实验室', path: routes.adminLabs, variant: 'secondary' },
  { title: '查看设备', path: routes.adminEquipment, variant: 'secondary' }
]

export const roleTextMap = {
  student: '学生',
  teacher: '老师',
  lab_admin: '实验室管理员',
  system_admin: '系统管理员'
}

export function getRoleText(role) {
  return roleTextMap[role] || '普通用户'
}

export function isTabRoute(path) {
  return userTabs.some((item) => item.path === path)
}

export function getAdminMenuGroups() {
  const map = {}
  adminMenus.forEach((item) => {
    if (!map[item.group]) map[item.group] = []
    map[item.group].push(item)
  })
  return Object.keys(map).map((group) => ({ group, items: map[group] }))
}

const SYSTEM_ADMIN_ONLY_PATHS = [routes.adminCampuses, routes.adminUsers]

export function getAdminMenusByRole(role) {
  if (role === 'system_admin') return adminMenus
  if (role === 'lab_admin') {
    return adminMenus.filter((item) => !SYSTEM_ADMIN_ONLY_PATHS.includes(item.path))
  }
  return []
}

export function canAccessAdminRoute(role, path) {
  if (!path) return false
  const routePath = path.startsWith('/') ? path : `/${path}`
  const extraAdminPaths = [routes.adminProfile]
  const adminPathSet = new Set(adminMenus.map((item) => item.path).concat(extraAdminPaths))
  if (!adminPathSet.has(routePath)) return false
  if (role === 'system_admin') return true
  if (role === 'lab_admin') return !SYSTEM_ADMIN_ONLY_PATHS.includes(routePath)
  return false
}

export function getDefaultAdminPath(role) {
  const availableMenus = getAdminMenusByRole(role)
  return availableMenus.length ? availableMenus[0].path : routes.home
}

export function getUserTopNavByRole(role) {
  if (role === 'teacher') {
    return [
      { key: 'home', title: '首页', path: routes.home },
      { key: 'campuses', title: '校区资源', path: routes.campuses },
      { key: 'labs', title: '实验室', path: routes.labs },
      { key: 'reserve', title: '教学预约', path: routes.reserve },
      { key: 'assetRequests', title: '资产申报', path: routes.assetRequests },
      { key: 'reservations', title: '我的预约', path: routes.myReservations },
      { key: 'agent', title: 'AI 助手', path: routes.agent }
    ]
  }
  if (role === 'student') {
    return userTopNav.filter((item) => item.key !== 'profile')
  }
  return userTopNav
}

export function isSystemAdmin(role) {
  return role === 'system_admin'
}

export function isLabAdmin(role) {
  return role === 'lab_admin'
}

export function canManageCampuses(role) {
  return isSystemAdmin(role)
}

export function canManageUsers(role) {
  return isSystemAdmin(role)
}

export function canManageLabs(role) {
  return isSystemAdmin(role) || isLabAdmin(role)
}

export function canManageEquipment(role) {
  return isSystemAdmin(role) || isLabAdmin(role)
}

export function canApproveReservations(role) {
  return isSystemAdmin(role) || isLabAdmin(role)
}

export function canViewStatistics(role) {
  return isSystemAdmin(role) || isLabAdmin(role)
}

export function canViewOperationLogs(role) {
  return isSystemAdmin(role) || isLabAdmin(role)
}
