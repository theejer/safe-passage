"""Rich-based console reporter for live test progress and results."""

from typing import Dict, Any, Optional
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' library not installed. Install with: pip install rich")


class ConsoleReporter:
    """Formatted console output for test execution and results."""
    
    def __init__(self, use_rich: bool = True):
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
        self.current_category = None
    
    def print_header(self):
        """Print test suite header."""
        if self.use_rich:
            header = Panel(
                "[bold cyan]Safe Passage Performance Test Suite v1.0[/bold cyan]\n"
                "Measuring heartbeat monitoring and emergency escalation reliability",
                box=None,
                padding=(1, 2)
            )
            self.console.print(header)
        else:
            print("=" * 70)
            print("  Safe Passage Performance Test Suite v1.0")
            print("  Measuring heartbeat monitoring and emergency escalation reliability")
            print("=" * 70)
            print()
    
    def start_category(self, category_name: str, category_num: int, total_categories: int):
        """Start a new test category."""
        self.current_category = category_name
        
        if self.use_rich:
            self.console.print(f"\n[bold][{category_num}/{total_categories}] {category_name}[/bold]")
        else:
            print(f"\n[{category_num}/{total_categories}] {category_name}")
    
    def print_test_result(self, test_name: str, passed: bool, value: Any = None, 
                         target: Any = None, indent: int = 2):
        """Print individual test result."""
        indent_str = " " * indent
        
        if self.use_rich:
            if passed:
                status = "[green]✓[/green]"
                color = "green"
            else:
                status = "[yellow]⚠[/yellow]"
                color = "yellow"
            
            result_text = f"{indent_str}├─ {test_name:<30}"
            if value is not None and target is not None:
                result_text += f" {status} {value} (target: {target})"
            elif value is not None:
                result_text += f" {status} {value}"
            else:
                result_text += f" {status}"
            
            self.console.print(result_text)
        else:
            status = "✓" if passed else "⚠"
            result_text = f"{indent_str}├─ {test_name:<30} {status}"
            if value is not None and target is not None:
                result_text += f" {value} (target: {target})"
            elif value is not None:
                result_text += f" {value}"
            print(result_text)
    
    def print_error(self, test_name: str, error: str, indent: int = 2):
        """Print test error."""
        indent_str = " " * indent
        
        if self.use_rich:
            self.console.print(f"{indent_str}├─ {test_name:<30} [red]✗[/red] {error}")
        else:
            print(f"{indent_str}├─ {test_name:<30} ✗ {error}")
    
    def print_summary(self, summary: Dict[str, Any], json_path: str, html_path: str):
        """Print final summary."""
        total = summary.get('total_tests', 0)
        passed = summary.get('passed', 0)
        warnings = summary.get('warnings', 0)
        failed = summary.get('failed', 0)
        duration = summary.get('duration_seconds', 0)
        
        if self.use_rich:
            self.console.print("\n" + "═" * 70)
            self.console.print("[bold]SUMMARY[/bold]".center(70))
            self.console.print("═" * 70)
            
            summary_text = (
                f"Total Tests: {total}       "
                f"[green]Passed: {passed} ✓[/green]       "
                f"[yellow]Warnings: {warnings} ⚠[/yellow]       "
                f"[red]Failed: {failed} ✗[/red]\n"
                f"Execution Time: {duration:.1f}s\n"
                f"Results: {json_path}\n"
                f"Report: {html_path}"
            )
            
            self.console.print(summary_text)
            self.console.print("═" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print("SUMMARY".center(70))
            print("=" * 70)
            print(f"Total Tests: {total}       Passed: {passed} ✓       "
                  f"Warnings: {warnings} ⚠       Failed: {failed} ✗")
            print(f"Execution Time: {duration:.1f}s")
            print(f"Results: {json_path}")
            print(f"Report: {html_path}")
            print("=" * 70 + "\n")
    
    def print_progress(self, message: str):
        """Print progress message."""
        if self.use_rich:
            self.console.print(f"  [dim]{message}[/dim]")
        else:
            print(f"  {message}")
    
    def create_progress_bar(self):
        """Create a progress bar context manager (Rich only)."""
        if self.use_rich:
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            )
        else:
            # Return a dummy context manager for non-Rich mode
            return DummyProgress()


class DummyProgress:
    """Dummy progress bar for when Rich is not available."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def add_task(self, description: str, total: int = 100):
        print(f"  {description}")
        return 0
    
    def update(self, task_id: int, advance: int = 1):
        pass
