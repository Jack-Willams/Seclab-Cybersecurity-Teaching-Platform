export interface User {
  userId: number
  userStudentNumber: string
  userPassword?: string
  userTel?: string
  userImage?: string
  userName: string
  userAcademy?: string
  userClass?: string
  userEmail?: string
  userGender?: number
  classId?: number
  createTime?: string
  role?: 'admin' | 'teacher' | 'student'
  status?: string
} 
