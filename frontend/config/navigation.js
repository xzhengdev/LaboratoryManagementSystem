// 统一维护三端页面路由、菜单、角色文案与快捷入口。
// 这样做的目的不是“为了抽象而抽象”，而是把信息架构从页面里抽出来，
// 后续无论调整小程序 Tab、PC 前台导航还是后台左侧菜单，都只需要改这一处。

export const routes = {
  login: '/pages/login/index',
  home: '/pages/home/index',
  campuses: '/pages/campuses/index',
  labs: '/pages/labs/index',
  labDetail: '/pages/lab-detail/index',
  schedule: '/pages/schedule/index',
  reserve: '/pages/reserve/index',
  myReservations: '/pages/my-reservations/index',
  reservationDetail: '/pages/reservation-detail/index',
  profile: '/pages/profile/index',
  agent: '/pages/agent/index',
  adminDashboard: '/pages/admin-dashboard/index',
  adminCampuses: '/pages/admin-campuses/index',
  adminLabs: '/pages/admin-labs/index',
  adminEquipment: '/pages/admin-equipment/index',
  adminApprovals: '/pages/admin-approvals/index',
  adminUsers: '/pages/admin-users/index',
  statistics: '/pages/statistics/index'
}

// 小程序端/移动端用户入口尽量保持 4 个核心 Tab。
// 即使当前还没有把原生 tabBar 资源图标补齐，页面层也可以先共享这份导航定义。
export const userTabs = [
  { key: 'home', title: '首页', path: routes.home, desc: '预约入口与推荐资源' },
  { key: 'labs', title: '实验室', path: routes.labs, desc: '按校区和条件查找实验室' },
  { key: 'reservations', title: '我的预约', path: routes.myReservations, desc: '跟踪状态与取消预约' },
  { key: 'profile', title: '我的', path: routes.profile, desc: '个人资料与快捷操作' }
]

export const userTopNav = [
  { key: 'home', title: '首页', path: routes.home },
  { key: 'campuses', title: '校区资源', path: routes.campuses },
  { key: 'labs', title: '实验室预约', path: routes.labs },
  { key: 'reservations', title: '我的预约', path: routes.myReservations },
  { key: 'agent', title: '智能助手', path: routes.agent },
  { key: 'profile', title: '个人中心', path: routes.profile }
]

export const userQuickEntries = [
  { title: '校区列表', desc: '查看各校区实验室分布与位置说明', path: routes.campuses, layout: 'card' },
  { title: '实验室列表', desc: '按校区、状态与关键词快速检索实验室', path: routes.labs, layout: 'filter-list' },
  { title: '我的预约', desc: '集中查看待审批、已通过与已取消记录', path: routes.myReservations, layout: 'table-mix' },
  { title: '个人中心', desc: '查看角色信息、校区归属和高频入口', path: routes.profile, layout: 'card' }
]

export const adminMenus = [
  { key: 'dashboard', title: '控制台首页', desc: '总览指标与快捷入口', path: routes.adminDashboard, group: '概览' },
  { key: 'campuses', title: '校区管理', desc: '维护校区信息与状态', path: routes.adminCampuses, group: '资源管理' },
  { key: 'labs', title: '实验室管理', desc: '维护实验室、开放时段与容量', path: routes.adminLabs, group: '资源管理' },
  { key: 'equipment', title: '设备管理', desc: '维护设备状态与所属实验室', path: routes.adminEquipment, group: '资源管理' },
  { key: 'approvals', title: '预约审批', desc: '处理待审批预约与驳回意见', path: routes.adminApprovals, group: '预约管理' },
  { key: 'users', title: '用户管理', desc: '维护用户角色、状态与校区归属', path: routes.adminUsers, group: '用户权限' },
  { key: 'statistics', title: '统计分析', desc: '查看校区、实验室与预约图表', path: routes.statistics, group: '分析看板' }
]

export const adminShortcutEntries = [
  { title: '处理审批', path: routes.adminApprovals, variant: 'primary' },
  { title: '维护实验室', path: routes.adminLabs, variant: 'secondary' },
  { title: '查看设备', path: routes.adminEquipment, variant: 'secondary' }
]

export const roleTextMap = {
  student: '学生',
  teacher: '教师',
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
