export interface DisplayQuestion{
    id: number
    content: string
    score: number
    requiresTarget: boolean
    type: 'single-choice' | 'multiple-choice' | 'open-ended-with-answer' | 'open-ended-without-answer'
}

export interface SingleChoiceQuestion extends DisplayQuestion {
    type: 'single-choice'
    options: string[]
}

export interface MultipleChoiceQuestion extends DisplayQuestion {
    type: 'multiple-choice'
    options: string[]
}

export interface OpenEndedWithAnswerQuestion extends DisplayQuestion {
    type: 'open-ended-with-answer' 
}

export interface OpenEndedWithoutAnswerQuestion extends DisplayQuestion {
    type: 'open-ended-without-answer'
}

export type DisplayQuestionType = SingleChoiceQuestion | MultipleChoiceQuestion | OpenEndedWithAnswerQuestion | OpenEndedWithoutAnswerQuestion
