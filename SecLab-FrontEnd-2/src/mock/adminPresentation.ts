export const DEMO_ADMIN_USER_COUNT = 128

export type AdminClassPresentation = {
  id: number
  name: string
  academy: string
  courseName: string
  studentCount: number
  overallScore: number
  riskStudents: number
  activeLevel: string
}

export const DEMO_ADMIN_CLASS_VIEWS: AdminClassPresentation[] = [
  {
    id: 2,
    name: '网络安全231班',
    academy: '网络安全学院',
    courseName: 'Web安全综合实训',
    studentCount: 43,
    overallScore: 86,
    riskStudents: 2,
    activeLevel: '高',
  },
  {
    id: 1,
    name: '网络安全232班',
    academy: '网络安全学院',
    courseName: 'Web安全综合实训',
    studentCount: 42,
    overallScore: 82,
    riskStudents: 3,
    activeLevel: '中',
  },
  {
    id: 3,
    name: '信息安全231班',
    academy: '信息工程学院',
    courseName: '高级攻防综合实训',
    studentCount: 43,
    overallScore: 89,
    riskStudents: 2,
    activeLevel: '极高',
  },
]

export const DEMO_ADMIN_CLASS_NAMES = DEMO_ADMIN_CLASS_VIEWS.map((item) => item.name)

export const DEMO_ADMIN_EMAIL_DOMAIN = 'stu.seclab.edu.cn'

export type AdminSpotlightStudent = {
  userName: string
  userGender: 0 | 1
  userStudentNumber: string
  userClass: string
  userAcademy: string
  progress: number
  status: string
}

export const DEMO_ADMIN_SPOTLIGHT_STUDENTS: AdminSpotlightStudent[] = [
  {
    userName: '周书铭',
    userGender: 1,
    userStudentNumber: '202323100001',
    userClass: DEMO_ADMIN_CLASS_VIEWS[0].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[0].academy,
    progress: 86,
    status: '课堂活跃',
  },
  {
    userName: '何宇安',
    userGender: 1,
    userStudentNumber: '202323100002',
    userClass: DEMO_ADMIN_CLASS_VIEWS[0].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[0].academy,
    progress: 82,
    status: '稳定推进',
  },
  {
    userName: '许若彤',
    userGender: 0,
    userStudentNumber: '202323100003',
    userClass: DEMO_ADMIN_CLASS_VIEWS[0].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[0].academy,
    progress: 74,
    status: '持续跟进',
  },
  {
    userName: '陈思远',
    userGender: 1,
    userStudentNumber: '202323200001',
    userClass: DEMO_ADMIN_CLASS_VIEWS[1].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[1].academy,
    progress: 92,
    status: '进度领先',
  },
  {
    userName: '刘子涵',
    userGender: 0,
    userStudentNumber: '202323200002',
    userClass: DEMO_ADMIN_CLASS_VIEWS[1].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[1].academy,
    progress: 78,
    status: '稳定推进',
  },
  {
    userName: '王嘉豪',
    userGender: 1,
    userStudentNumber: '202323200003',
    userClass: DEMO_ADMIN_CLASS_VIEWS[1].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[1].academy,
    progress: 63,
    status: '重点关注',
  },
  {
    userName: '林一鸣',
    userGender: 1,
    userStudentNumber: '202323300001',
    userClass: DEMO_ADMIN_CLASS_VIEWS[2].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[2].academy,
    progress: 88,
    status: '课堂活跃',
  },
  {
    userName: '姜嘉宁',
    userGender: 0,
    userStudentNumber: '202323300002',
    userClass: DEMO_ADMIN_CLASS_VIEWS[2].name,
    userAcademy: DEMO_ADMIN_CLASS_VIEWS[2].academy,
    progress: 79,
    status: '稳定推进',
  },
]
