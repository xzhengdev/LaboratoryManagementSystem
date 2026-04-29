import { request } from "./request";
import { getToken } from "../common/session";
import { getApiBaseUrl } from "../common/platform";

const BASE_URL = getApiBaseUrl();
const API_ORIGIN = String(BASE_URL || "").replace(/\/api\/?$/, "");
const createIdempotencyKey = () =>
  `resv-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
const createAssetIdempotencyKey = () =>
  `asset-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

const normalizeMediaUrl = (rawUrl) => {
  const text = String(rawUrl || "").trim();
  if (!text) return "";
  if (/^https?:\/\//i.test(text)) return text;
  if (text.startsWith("//")) {
    const protocol = typeof window !== "undefined" ? window.location.protocol : "http:";
    return `${protocol}${text}`;
  }
  if (text.startsWith("/")) return `${API_ORIGIN}${text}`;
  return `${API_ORIGIN}/${text}`;
};

const normalizePhotoObjects = (photos) => {
  if (!Array.isArray(photos)) return [];
  return photos.map((item) => ({
    ...item,
    url: normalizeMediaUrl(item?.url),
  }));
};

const normalizeLabPhotos = (photos) => {
  if (!Array.isArray(photos)) return [];
  return photos.map((item) => normalizeMediaUrl(item));
};

export const api = {
  login: (data) => request({ url: "/auth/login", method: "POST", data }),
  profile: () => request({ url: "/auth/profile" }),
  updateProfile: (data) =>
    request({ url: "/auth/profile", method: "PUT", data }),
  changePassword: (data) =>
    request({ url: "/auth/change-password", method: "POST", data }),
  uploadAvatar: (filePath) =>
    new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${BASE_URL}/auth/upload-avatar`,
        filePath,
        name: "file",
        header: {
          Authorization: getToken() ? `Bearer ${getToken()}` : "",
        },
        success: (res) => {
          const raw = res.data;
          let payload = {};
          if (raw && typeof raw === "object") {
            payload = raw;
          } else {
            try {
              payload = JSON.parse(raw || "{}");
            } catch (_error) {
              payload = {};
            }
          }

          if (
            res.statusCode === 200 &&
            payload.code === 0 &&
            payload.data &&
            payload.data.url
          ) {
            resolve({ ...payload.data, url: normalizeMediaUrl(payload.data.url) });
            return;
          }

          const errorText =
            payload.message || `头像上传失败(${res.statusCode})`;
          uni.showToast({ title: errorText, icon: "none" });
          console.error("upload-avatar failed:", {
            statusCode: res.statusCode,
            body: res.data,
          });
          reject(payload);
        },
        fail: (error) => {
          uni.showToast({ title: "头像上传失败，请检查网络", icon: "none" });
          reject(error);
        },
      });
    }),
  uploadLabPhoto: (filePath) =>
    new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${BASE_URL}/labs/upload-photo`,
        filePath,
        name: "file",
        header: {
          Authorization: getToken() ? `Bearer ${getToken()}` : "",
        },
        success: (res) => {
          const raw = res.data;
          let payload = {};
          if (raw && typeof raw === "object") {
            payload = raw;
          } else {
            try {
              payload = JSON.parse(raw || "{}");
            } catch (_error) {
              payload = {};
            }
          }

          if (
            res.statusCode === 200 &&
            payload.code === 0 &&
            payload.data &&
            payload.data.url
          ) {
            resolve({ ...payload.data, url: normalizeMediaUrl(payload.data.url) });
            return;
          }

          const errorText =
            payload.message || `实验室封面上传失败(${res.statusCode})`;
          uni.showToast({ title: errorText, icon: "none" });
          reject(payload);
        },
        fail: (error) => {
          uni.showToast({
            title: "实验室封面上传失败，请检查网络",
            icon: "none",
          });
          reject(error);
        },
      });
    }),
  uploadCampusCover: (filePath) =>
    new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${BASE_URL}/campuses/upload-cover`,
        filePath,
        name: "file",
        header: {
          Authorization: getToken() ? `Bearer ${getToken()}` : "",
        },
        success: (res) => {
          const raw = res.data;
          let payload = {};
          if (raw && typeof raw === "object") {
            payload = raw;
          } else {
            try {
              payload = JSON.parse(raw || "{}");
            } catch (_error) {
              payload = {};
            }
          }

          if (
            res.statusCode === 200 &&
            payload.code === 0 &&
            payload.data &&
            payload.data.url
          ) {
            resolve({ ...payload.data, url: normalizeMediaUrl(payload.data?.url) });
            return;
          }

          const errorText =
            payload.message || `校区封面上传失败(${res.statusCode})`;
          uni.showToast({ title: errorText, icon: "none" });
          reject(payload);
        },
        fail: (error) => {
          uni.showToast({
            title: "校区封面上传失败，请检查网络",
            icon: "none",
          });
          reject(error);
        },
      });
    }),
  campuses: async () => {
    const rows = await request({ url: "/campuses" });
    if (!Array.isArray(rows)) return rows;
    return rows.map((item) => ({ ...item, cover_url: normalizeMediaUrl(item?.cover_url) }));
  },
  createCampus: (data) => request({ url: "/campuses", method: "POST", data }),
  updateCampus: (id, data) =>
    request({ url: `/campuses/${id}`, method: "PUT", data }),
  deleteCampus: (id) => request({ url: `/campuses/${id}`, method: "DELETE" }),
  labs: async (params = {}) => {
    const data = await request({ url: "/labs", data: params });
    if (Array.isArray(data)) {
      return data.map((item) => ({ ...item, photos: normalizeLabPhotos(item?.photos) }));
    }
    if (data && Array.isArray(data.items)) {
      return {
        ...data,
        items: data.items.map((item) => ({ ...item, photos: normalizeLabPhotos(item?.photos) })),
      };
    }
    return data;
  },
  equipment: (params = {}) => request({ url: "/equipment", data: params }),
  createEquipment: (data) =>
    request({ url: "/equipment", method: "POST", data }),
  updateEquipment: (id, data) =>
    request({ url: `/equipment/${id}`, method: "PUT", data }),
  deleteEquipment: (id) =>
    request({ url: `/equipment/${id}`, method: "DELETE" }),
  createLab: (data) => request({ url: "/labs", method: "POST", data }),
  updateLab: (id, data) => request({ url: `/labs/${id}`, method: "PUT", data }),
  deleteLab: (id) => request({ url: `/labs/${id}`, method: "DELETE" }),
  labDetail: async (id) => {
    const item = await request({ url: `/labs/${id}` });
    if (!item || typeof item !== "object") return item;
    return { ...item, photos: normalizeLabPhotos(item?.photos) };
  },
  labSchedule: (id, date) =>
    request({ url: `/labs/${id}/schedule`, data: { date } }),
  createReservation: (data, options = {}) =>
    request({
      url: "/reservations",
      method: "POST",
      data,
      headers: {
        "Idempotency-Key": options.idempotencyKey || createIdempotencyKey(),
      },
    }),
  myReservations: () => request({ url: "/reservations/my" }),
  reservations: (params = {}) =>
    request({ url: "/reservations", data: params }),
  reservationDetail: (id) => request({ url: `/reservations/${id}` }),
  cancelReservation: (id) =>
    request({ url: `/reservations/${id}/cancel`, method: "POST" }),
  pendingApprovals: () => request({ url: "/approvals/pending" }),
  approvalAction: (id, data) =>
    request({ url: `/approvals/${id}`, method: "POST", data }),
  users: (params = {}) => request({ url: "/users", data: params }),
  createUser: (data) => request({ url: "/users", method: "POST", data }),
  updateUser: (id, data) =>
    request({ url: `/users/${id}`, method: "PUT", data }),
  deleteUser: (id) => request({ url: `/users/${id}`, method: "DELETE" }),
  resetUserPassword: (id, data = {}) =>
    request({ url: `/users/${id}/reset-password`, method: "POST", data }),
  operationLogs: (params = {}) =>
    request({ url: "/operation-logs", data: params }),
  statisticsOverview: () => request({ url: "/statistics/overview" }),
  statisticsCampus: () => request({ url: "/statistics/campus" }),
  statisticsUsage: () => request({ url: "/statistics/lab_usage" }),
  statisticsDailyReportOverview: () =>
    request({ url: "/statistics/daily-report/overview" }),
  statisticsDailyReportCampus: () =>
    request({ url: "/statistics/daily-report/campus" }),
  statisticsDailyReportLab: () =>
    request({ url: "/statistics/daily-report/lab" }),
  currentAssetBudget: (params = {}) =>
    request({ url: "/asset-budgets/current", data: params }),
  updateAssetBudget: (campusId, data) =>
    request({ url: `/asset-budgets/${campusId}`, method: "PUT", data }),
  createAssetRequest: (data, options = {}) =>
    request({
      url: "/asset-requests",
      method: "POST",
      data,
      headers: {
        "Idempotency-Key":
          options.idempotencyKey || createAssetIdempotencyKey(),
      },
    }),
  assetRequests: (params = {}) => request({ url: "/asset-requests", data: params }),
  reviewAssetRequest: (id, data) =>
    request({ url: `/asset-requests/${id}/review`, method: "POST", data }),
  stockInAsset: (id, data = {}) =>
    request({ url: `/asset-requests/${id}/stock-in`, method: "POST", data }),
  assets: async (params = {}) => {
    const rows = await request({ url: "/assets", data: params });
    if (!Array.isArray(rows)) return rows;
    return rows.map((item) => ({
      ...item,
      photos: normalizePhotoObjects(item?.photos),
    }));
  },
  dailyReports: async (params = {}) => {
    const rows = await request({ url: "/lab-reports", data: params });
    if (!Array.isArray(rows)) return rows;
    return rows.map((item) => ({
      ...item,
      photos: normalizePhotoObjects(item?.photos),
    }));
  },
  createDailyReport: (data) =>
    request({ url: "/lab-reports", method: "POST", data }),
  reviewDailyReport: (id, data) =>
    request({ url: `/lab-reports/${id}/review`, method: "POST", data }),
  uploadDailyReportPhoto: (filePath, data = {}) =>
    new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${BASE_URL}/lab-reports/photos/upload`,
        filePath,
        name: "file",
        formData: data,
        header: {
          Authorization: getToken() ? `Bearer ${getToken()}` : "",
        },
        success: (res) => {
          const raw = res.data;
          let payload = {};
          if (raw && typeof raw === "object") {
            payload = raw;
          } else {
            try {
              payload = JSON.parse(raw || "{}");
            } catch (_error) {
              payload = {};
            }
          }
          if (res.statusCode === 200 && payload.code === 0 && payload.data) {
            resolve({ ...payload.data, url: normalizeMediaUrl(payload.data?.url) });
            return;
          }
          uni.showToast({
            title: payload.message || `日报图片上传失败(${res.statusCode})`,
            icon: "none",
          });
          reject(payload);
        },
        fail: (error) => {
          uni.showToast({ title: "日报图片上传失败，请检查网络", icon: "none" });
          reject(error);
        },
      });
    }),
  notifications: (params = {}) => request({ url: "/notifications", data: params }),
  notificationUnreadCount: () => request({ url: "/notifications/unread-count" }),
  markNotificationRead: (id) =>
    request({ url: `/notifications/${id}/read`, method: "POST" }),
  markAllNotificationsRead: () =>
    request({ url: "/notifications/read-all", method: "POST" }),
  syncSummary: () =>
    request({ url: "/statistics/summary/sync", method: "POST" }),
  latestSummary: () =>
    request({ url: "/statistics/summary/latest" }),
  uploadAssetPhoto: (assetId, filePath) =>
    new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${BASE_URL}/assets/${assetId}/photos/upload`,
        filePath,
        name: "file",
        header: {
          Authorization: getToken() ? `Bearer ${getToken()}` : "",
        },
        success: (res) => {
          const raw = res.data;
          let payload = {};
          if (raw && typeof raw === "object") {
            payload = raw;
          } else {
            try {
              payload = JSON.parse(raw || "{}");
            } catch (_error) {
              payload = {};
            }
          }
          if (res.statusCode === 200 && payload.code === 0 && payload.data) {
            resolve({ ...payload.data, url: normalizeMediaUrl(payload.data?.url) });
            return;
          }
          uni.showToast({
            title: payload.message || `资产图片上传失败(${res.statusCode})`,
            icon: "none",
          });
          reject(payload);
        },
        fail: (error) => {
          uni.showToast({ title: "资产图片上传失败，请检查网络", icon: "none" });
          reject(error);
        },
      });
    }),
  agentChat: (message) =>
    request({ url: "/agent/chat", method: "POST", data: { message } }),
};

