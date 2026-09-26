import type { User } from '../types/user'
import {
  DEMO_ADMIN_CLASS_VIEWS,
  DEMO_ADMIN_EMAIL_DOMAIN,
  DEMO_ADMIN_SPOTLIGHT_STUDENTS,
  DEMO_ADMIN_USER_COUNT,
} from './adminPresentation'

type PresentationStudentSeed = {
  userName: string
  userGender: 0 | 1
  userStudentNumber?: string
  userAcademy?: string
  userClass?: string
}

const buildNameSeeds = (
  familyNames: string[],
  givenNames: string[],
  userGender: 0 | 1,
): PresentationStudentSeed[] =>
  familyNames.flatMap((family) =>
    givenNames.map((given) => ({
      userName: `${family}${given}`,
      userGender,
    })),
  )

const priorityPresentationStudents: PresentationStudentSeed[] =
  DEMO_ADMIN_SPOTLIGHT_STUDENTS.map((item) => ({
    userName: item.userName,
    userGender: item.userGender,
    userStudentNumber: item.userStudentNumber,
    userAcademy: item.userAcademy,
    userClass: item.userClass,
  }))

const malePresentationStudents = buildNameSeeds(
  ['周', '何', '陈', '刘', '王', '林', '郭', '郑', '许', '杨'],
  ['书铭', '思远', '嘉豪', '宇安', '一鸣', '景行', '知远', '泽恺', '子轩', '浩宸'],
  1,
)

const femalePresentationStudents = buildNameSeeds(
  ['许', '沐', '苏', '沈', '姜', '顾', '乔', '宋', '温', '安'],
  ['若彤', '语桐', '可欣', '沐晴', '嘉宁', '安琦', '星冉', '知夏', '雨桐', '思羽'],
  0,
)

const demoClassConfigs = DEMO_ADMIN_CLASS_VIEWS.map((item) => ({
  name: item.name,
  academy: item.academy,
  studentCount: item.studentCount,
}))

export const buildPresentationUsers = (): User[] => {
  const classStudentNumberPrefixes = ['20232310', '20232320', '20232330']
  const presentationUsers: User[] = []
  const usedNames = new Set(priorityPresentationStudents.map((item) => item.userName))
  const spotlightByClass = new Map<string, PresentationStudentSeed[]>()
  const malePool = malePresentationStudents.filter((item) => !usedNames.has(item.userName))
  const femalePool = femalePresentationStudents.filter((item) => !usedNames.has(item.userName))
  let maleIndex = 0
  let femaleIndex = 0
  let globalIndex = 0

  priorityPresentationStudents.forEach((item) => {
    const className = item.userClass || demoClassConfigs[0].name
    const classSeeds = spotlightByClass.get(className) || []
    classSeeds.push(item)
    spotlightByClass.set(className, classSeeds)
  })

  demoClassConfigs.forEach((classConfig, classIndex) => {
    const classPrefix = classStudentNumberPrefixes[classIndex] || '20232390'
    const classSeeds = [...(spotlightByClass.get(classConfig.name) || [])]
    let preferMale = classIndex !== 1

    for (let classOffset = 0; classOffset < classConfig.studentCount; classOffset += 1) {
      let studentSeed = classSeeds.shift()

      if (!studentSeed) {
        const primaryPool = preferMale ? malePool : femalePool
        const secondaryPool = preferMale ? femalePool : malePool
        const primaryIndex = preferMale ? maleIndex : femaleIndex
        const secondaryIndex = preferMale ? femaleIndex : maleIndex

        studentSeed = primaryPool[primaryIndex] || secondaryPool[secondaryIndex]
        if (!studentSeed) {
          break
        }

        if (preferMale && primaryPool[primaryIndex]) {
          maleIndex += 1
        } else if (!preferMale && primaryPool[primaryIndex]) {
          femaleIndex += 1
        } else if (preferMale) {
          femaleIndex += 1
        } else {
          maleIndex += 1
        }
      }

      const studentNumber =
        studentSeed.userStudentNumber ||
        `${classPrefix}${String(classOffset + 1).padStart(4, '0')}`

      presentationUsers.push({
        userId: 1000 + globalIndex + 1,
        userStudentNumber: studentNumber,
        userName: studentSeed.userName,
        userEmail: `${studentNumber}@${DEMO_ADMIN_EMAIL_DOMAIN}`,
        userTel: `1380013${String(8100 + globalIndex).slice(-4)}`,
        userAcademy: studentSeed.userAcademy || classConfig.academy,
        userClass: studentSeed.userClass || classConfig.name,
        userGender: studentSeed.userGender,
        createTime: `2026-04-${String((globalIndex % 28) + 1).padStart(2, '0')} ${String(
          8 + (globalIndex % 10),
        ).padStart(2, '0')}:${String((globalIndex * 7) % 60).padStart(2, '0')}:00`,
      })

      preferMale = !preferMale
      globalIndex += 1
    }
  })

  return presentationUsers.slice(0, DEMO_ADMIN_USER_COUNT)
}

export const PRESENTATION_STUDENTS = buildPresentationUsers()
