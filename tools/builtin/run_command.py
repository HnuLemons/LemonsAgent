import subprocess


def run_shell_command(command: str, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return f"Error: 命令执行超时（超过 {timeout} 秒）: {command}"
    except Exception as exc:
        return f"Error: 命令执行失败: {exc}"
    return result.stdout or result.stderr
