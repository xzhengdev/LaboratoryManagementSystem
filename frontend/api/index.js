import { request } from './request'

// 统一收口所有后端接口，页面层只关心“调用哪个业务方法”，
// 不再关心具体 URL 和请求方式，方便后续整体调整。
export const api = {
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  profile: () => request({ url: '/auth/profile' }),
  campuses: () => request({ url: '/campuses' }),
  labs: (params = {}) => request({ url: '/labs', data: params }),
  equipment: (params = {}) => request({ url: '/equipment', data: params }),
  createLab: (data) => request({ url: '/labs', method: 'POST', data }),
  updateLab: (id, data) => request({ url: `/labs/${id}`, method: 'PUT', data }),
  deleteLab: (id) => request({ url: `/labs/${id}`, method: 'DELETE' }),
  labDetail: (id) => request({ url: `/labs/${id}` }),
  labSchedule: (id, date) => request({ url: `/labs/${id}/schedule`, data: { date } }),
  createReservation: (data) => request({ url: '/reservations', method: 'POST', data }),
  myReservations: () => request({ url: '/reservations/my' }),
  reservations: (params = {}) => request({ url: '/reservations', data: params }),
  reservationDetail: (id) => request({ url: `/reservations/${id}` }),
  cancelReservation: (id) => request({ url: `/reservations/${id}/cancel`, method: 'POST' }),
  pendingApprovals: () => request({ url: '/approvals/pending' }),
  approvalAction: (id, data) => request({ url: `/approvals/${id}`, method: 'POST', data }),
  statisticsOverview: () => request({ url: '/statistics/overview' }),
  statisticsCampus: () => request({ url: '/statistics/campus' }),
  statisticsUsage: () => request({ url: '/statistics/lab_usage' }),
  agentChat: (message) => request({ url: '/agent/chat', method: 'POST', data: { message } })
}
