# SecLab-FrontEnd 项目结构

本文档描述了SecLab-FrontEnd项目的目录结构和各文件功能。

## 根目录文件

- `index.html` - 项目HTML入口文件，包含基本HTML结构和Vue挂载点
- `package.json` - 项目依赖配置文件，管理项目依赖包和脚本命令
- `yarn.lock` - Yarn包管理器锁定文件，确保依赖版本一致性
- `package-lock.json` - NPM包管理器锁定文件，确保依赖版本一致性
- `vite.config.ts` - Vite构建工具配置文件
- `tailwind.config.ts` - Tailwind CSS框架配置文件
- `postcss.config.js` - PostCSS配置文件，用于CSS转换处理
- `tsconfig.json` - TypeScript主配置文件
- `tsconfig.app.json` - 应用特定的TypeScript配置
- `tsconfig.node.json` - Node.js环境的TypeScript配置
- `README.md` - 项目说明文档
- `.gitignore` - Git忽略文件配置
- `upload.ps1` - PowerShell上传脚本
- `Test.ps1` - PowerShell测试脚本

## 目录结构

### src/ - 源代码目录

- `main.ts` - 应用入口文件，初始化Vue应用并引入各种插件和资源
- `App.vue` - 根Vue组件
- `api.ts` - API请求接口定义
- `common.ts` - 通用工具函数
- `style.css` - 全局样式文件
- `vite-env.d.ts` - Vite环境类型声明文件

#### src/router/ - 路由配置目录

- `router.ts` - Vue Router路由配置，定义应用的所有路由规则

#### src/pages/ - 页面组件目录

- `WelCome/` - 欢迎页面
- `User/` - 用户相关页面
  - `Courses/` - 课程列表页面
  - `Course/` - 单个课程详情页面
  - `Module/` - 单个模块详情页面
  - `Modules/` - 模块列表页面
  - `Profile/` - 用户个人资料页面
  - `Scoreboard/` - 积分榜页面
- `Admin/` - 管理员相关页面
  - `Users/` - 用户管理页面
  - `Courses/` - 课程管理页面
  - `Labs/` - 实验室管理页面
  - `DashBoard/` - 管理控制台页面
- `Access/` - 登录/认证相关页面

#### src/components/ - 可复用组件目录

- `MarkdownRenderer.vue` - Markdown渲染组件
- `NavMenuItem.vue` - 导航菜单项组件
- `Toast.vue` - 提示消息组件
- `icons/` - 图标组件目录

#### src/layout/ - 布局组件目录

- `User/` - 用户界面布局
- `Admin/` - 管理员界面布局

#### src/store/ - 状态管理目录

- `index.ts` - Pinia状态管理入口文件

#### src/types/ - TypeScript类型定义目录

存放项目中使用的TypeScript接口、类型和枚举定义

#### src/mock/ - 模拟数据目录

- `MockTarget.vue` - 模拟目标组件，用于开发测试

#### src/assets/ - 静态资源目录

存放图片、字体等静态资源文件

### public/ - 公共资源目录

存放不需要通过构建工具处理的静态文件

### dist/ - 构建输出目录

存放项目构建后的输出文件，用于部署

### .vscode/ - VS Code配置目录

存放VS Code编辑器相关配置

### .idea/ - JetBrains IDE配置目录

存放JetBrains IDE（如WebStorm）相关配置

### node_modules/ - 依赖包目录

存放项目依赖的第三方包

## 技术栈

- 前端框架: Vue 3
- 构建工具: Vite
- 语言: TypeScript
- CSS框架: Tailwind CSS, DaisyUI
- 路由: Vue Router
- 状态管理: Pinia
- 代码高亮: highlight.js
- HTTP客户端: Axios
- Markdown渲染: markdown-it 