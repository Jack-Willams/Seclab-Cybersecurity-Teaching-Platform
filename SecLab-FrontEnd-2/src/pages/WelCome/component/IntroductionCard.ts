export interface Props {
    title: string;
    description: string;
    svgPath: string;
    buttonText: string;
    buttonClass?: string;
    onClick?: () => void;
    icon?: string;
    highlight?: boolean;
  }