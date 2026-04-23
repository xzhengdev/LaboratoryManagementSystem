import { request } from "./request";
import { getToken } from "../common/session";
import { getApiBaseUrl } from "../common/platform";

const BASE_URL = getApiBaseUrl();

export const api = {
  login: (data) => request({ url: "/auth/login", method: "POST", data }),
  profile: () => request({ url: "/auth/profile" }),
  updateProfile: (data) =>
    request({ url: "/auth/profile", method: "PUT", data }),
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
            resolve(payload.data);
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
            resolve(payload.data);
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
            resolve(payload.data);
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
  campuses: () => request({ url: "/campuses" }),
  createCampus: (data) => request({ url: "/campuses", method: "POST", data }),
  updateCampus: (id, data) =>
    request({ url: `/campuses/${id}`, method: "PUT", data }),
  deleteCampus: (id) => request({ url: `/campuses/${id}`, method: "DELETE" }),
  labs: (params = {}) => request({ url: "/labs", data: params }),
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
  labDetail: (id) => request({ url: `/labs/${id}` }),
  labSchedule: (id, date) =>
    request({ url: `/labs/${id}/schedule`, data: { date } }),
  createReservation: (data) =>
    request({ url: "/reservations", method: "POST", data }),
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
  resetUserPassword: (id, data = {}) =>
    request({ url: `/users/${id}/reset-password`, method: "POST", data }),
  operationLogs: (params = {}) =>
    request({ url: "/operation-logs", data: params }),
  statisticsOverview: () => request({ url: "/statistics/overview" }),
  statisticsCampus: () => request({ url: "/statistics/campus" }),
  statisticsUsage: () => request({ url: "/statistics/lab_usage" }),
  agentChat: (message) =>
    request({ url: "/agent/chat", method: "POST", data: { message } }),
};
