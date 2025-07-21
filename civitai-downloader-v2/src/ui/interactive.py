#!/usr/bin/env python3
"""
Interactive User Interface System.
Implements requirement 19.3: Interactive CLI with user prompts and menu systems.
"""

import logging
import sys
import termios
import tty
import select
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import shutil
import time

logger = logging.getLogger(__name__)


class InputType(Enum):
    """Types of user input."""
    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    BOOLEAN = "boolean"
    PASSWORD = "password"
    MULTILINE = "multiline"


@dataclass
class ValidationRule:
    """Input validation rule."""
    rule_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: str = "Invalid input"
    
    def validate(self, value: Any) -> bool:
        """Validate input value."""
        if self.rule_type == "required" and not value:
            return False
        elif self.rule_type == "min_length" and len(str(value)) < self.parameters.get("length", 0):
            return False
        elif self.rule_type == "max_length" and len(str(value)) > self.parameters.get("length", float('inf')):
            return False
        elif self.rule_type == "range" and not (self.parameters.get("min", float('-inf')) <= value <= self.parameters.get("max", float('inf'))):
            return False
        elif self.rule_type == "pattern" and not self.parameters.get("regex").match(str(value)):
            return False
        
        return True


@dataclass
class UserPrompt:
    """User input prompt configuration."""
    prompt_id: str
    message: str
    input_type: InputType
    default_value: Optional[Any] = None
    choices: Optional[List[Any]] = None
    validation_rules: List[ValidationRule] = field(default_factory=list)
    help_text: Optional[str] = None
    required: bool = True
    sensitive: bool = False  # For password fields
    
    def validate_input(self, value: Any) -> tuple[bool, str]:
        """Validate user input against rules."""
        for rule in self.validation_rules:
            if not rule.validate(value):
                return False, rule.error_message
        return True, ""


@dataclass
class MenuOption:
    """Menu option definition."""
    key: str
    label: str
    description: Optional[str] = None
    action: Optional[Callable] = None
    submenu: Optional['Menu'] = None
    enabled: bool = True
    separator_after: bool = False


@dataclass
class Menu:
    """Interactive menu system."""
    title: str
    options: List[MenuOption] = field(default_factory=list)
    show_quit: bool = True
    show_back: bool = False
    parent_menu: Optional['Menu'] = None
    
    def add_option(self, option: MenuOption) -> None:
        """Add menu option."""
        self.options.append(option)
    
    def add_separator(self) -> None:
        """Add visual separator."""
        if self.options:
            self.options[-1].separator_after = True


class InteractiveInterface:
    """
    Interactive command-line interface system.
    Implements requirement 19.3: Rich interactive CLI experience.
    """
    
    def __init__(self, app_name: str = "CivitAI Downloader"):
        """
        Initialize interactive interface.
        
        Args:
            app_name: Application name for display
        """
        self.app_name = app_name
        self.terminal_width = shutil.get_terminal_size().columns
        self.terminal_height = shutil.get_terminal_size().lines
        
        # Interface state
        self.current_menu: Optional[Menu] = None
        self.input_history: List[str] = []
        self.session_data: Dict[str, Any] = {}
        
        # Styling configuration
        self.colors = {
            'primary': '\033[94m',    # Blue
            'success': '\033[92m',    # Green
            'warning': '\033[93m',    # Yellow
            'error': '\033[91m',      # Red
            'info': '\033[96m',       # Cyan
            'reset': '\033[0m',       # Reset
            'bold': '\033[1m',        # Bold
            'dim': '\033[2m'          # Dim
        }
        
        # Unicode characters for better visuals
        self.chars = {
            'arrow_right': '→',
            'bullet': '•',
            'check': '✓',
            'cross': '✗',
            'star': '★',
            'info': 'ℹ',
            'warning': '⚠',
            'error': '✖',
            'question': '?',
            'bar_horizontal': '─',
            'bar_vertical': '│',
            'corner_top_left': '┌',
            'corner_top_right': '┐',
            'corner_bottom_left': '└',
            'corner_bottom_right': '┘'
        }
        
        # Check if terminal supports colors
        self.color_support = self._check_color_support()
    
    def _check_color_support(self) -> bool:
        """Check if terminal supports colors."""
        return sys.stdout.isatty()
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if supported."""
        if not self.color_support:
            return text
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def clear_screen(self) -> None:
        """Clear terminal screen."""
        print('\033[2J\033[H', end='')
        sys.stdout.flush()
    
    def print_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Print formatted header."""
        width = min(80, self.terminal_width)
        
        # Top border
        print(self._colorize('┌' + '─' * (width - 2) + '┐', 'primary'))
        
        # Title line
        title_line = f"│ {title:^{width-4}} │"
        print(self._colorize(title_line, 'primary'))
        
        # Subtitle if provided
        if subtitle:
            subtitle_line = f"│ {subtitle:^{width-4}} │"
            print(self._colorize(subtitle_line, 'info'))
        
        # Bottom border
        print(self._colorize('└' + '─' * (width - 2) + '┘', 'primary'))
        print()
    
    def print_section(self, title: str, content: Optional[str] = None) -> None:
        """Print formatted section."""
        section_title = f"{self.chars['star']} {title}"
        print(self._colorize(section_title, 'bold'))
        
        if content:
            # Indent content
            for line in content.split('\n'):
                print(f"  {line}")
        print()
    
    def print_info(self, message: str, icon: bool = True) -> None:
        """Print info message."""
        icon_char = f"{self.chars['info']} " if icon else ""
        print(self._colorize(f"{icon_char}{message}", 'info'))
    
    def print_success(self, message: str, icon: bool = True) -> None:
        """Print success message."""
        icon_char = f"{self.chars['check']} " if icon else ""
        print(self._colorize(f"{icon_char}{message}", 'success'))
    
    def print_warning(self, message: str, icon: bool = True) -> None:
        """Print warning message."""
        icon_char = f"{self.chars['warning']} " if icon else ""
        print(self._colorize(f"{icon_char}{message}", 'warning'))
    
    def print_error(self, message: str, icon: bool = True) -> None:
        """Print error message."""
        icon_char = f"{self.chars['error']} " if icon else ""
        print(self._colorize(f"{icon_char}{message}", 'error'))
    
    def prompt_user(self, prompt: UserPrompt) -> Any:
        """
        Prompt user for input with validation.
        
        Args:
            prompt: UserPrompt configuration
            
        Returns:
            Validated user input
        """
        while True:
            # Display prompt message
            if prompt.help_text:
                print(self._colorize(f"{self.chars['info']} {prompt.help_text}", 'dim'))
            
            prompt_text = f"{self.chars['question']} {prompt.message}"
            
            # Add default value hint
            if prompt.default_value is not None:
                prompt_text += f" [{prompt.default_value}]"
            
            # Add choices for choice type
            if prompt.input_type == InputType.CHOICE and prompt.choices:
                choices_text = "/".join(str(c) for c in prompt.choices)
                prompt_text += f" ({choices_text})"
            
            prompt_text += ": "
            
            try:
                # Get input based on type
                if prompt.input_type == InputType.PASSWORD:
                    import getpass
                    raw_input = getpass.getpass(prompt_text)
                elif prompt.input_type == InputType.MULTILINE:
                    print(prompt_text)
                    print("(Enter empty line to finish)")
                    lines = []
                    while True:
                        line = input("> ")
                        if not line:
                            break
                        lines.append(line)
                    raw_input = "\n".join(lines)
                else:
                    raw_input = input(prompt_text)
                
                # Handle default value
                if not raw_input and prompt.default_value is not None:
                    raw_input = str(prompt.default_value)
                
                # Handle required check
                if prompt.required and not raw_input:
                    self.print_error("This field is required.")
                    continue
                
                # Convert input based on type
                processed_input = self._process_input(raw_input, prompt)
                
                # Validate input
                valid, error_message = prompt.validate_input(processed_input)
                
                if not valid:
                    self.print_error(error_message)
                    continue
                
                # Store in history (non-sensitive only)
                if not prompt.sensitive:
                    self.input_history.append(raw_input)
                
                return processed_input
                
            except KeyboardInterrupt:
                print("\n")
                raise
            except EOFError:
                print("\n")
                return None
    
    def _process_input(self, raw_input: str, prompt: UserPrompt) -> Any:
        """Process raw input based on prompt type."""
        if prompt.input_type == InputType.NUMBER:
            try:
                if '.' in raw_input:
                    return float(raw_input)
                else:
                    return int(raw_input)
            except ValueError:
                raise ValueError("Please enter a valid number") from None
        
        elif prompt.input_type == InputType.BOOLEAN:
            lower_input = raw_input.lower()
            if lower_input in ['y', 'yes', 'true', '1']:
                return True
            elif lower_input in ['n', 'no', 'false', '0']:
                return False
            else:
                raise ValueError("Please enter yes/no, true/false, or y/n")
        
        elif prompt.input_type == InputType.CHOICE:
            if prompt.choices and raw_input in [str(c) for c in prompt.choices]:
                # Find the original choice value
                for choice in prompt.choices:
                    if str(choice) == raw_input:
                        return choice
            raise ValueError(f"Please choose from: {', '.join(str(c) for c in prompt.choices)}")
        
        else:
            return raw_input
    
    def display_menu(self, menu: Menu) -> Optional[str]:
        """
        Display menu and get user selection.
        
        Args:
            menu: Menu to display
            
        Returns:
            Selected option key or None for quit
        """
        self.current_menu = menu
        
        while True:
            # Clear screen and show header
            self.clear_screen()
            self.print_header(menu.title, self.app_name)
            
            # Display menu options
            enabled_options = []
            
            for i, option in enumerate(menu.options):
                if not option.enabled:
                    continue
                
                key_display = f"[{option.key}]"
                option_line = f"  {key_display:<6} {option.label}"
                
                if option.description:
                    option_line += f" - {self._colorize(option.description, 'dim')}"
                
                print(option_line)
                enabled_options.append(option)
                
                # Add separator if specified
                if option.separator_after:
                    print()
            
            print()  # Spacing
            
            # Standard navigation options
            nav_options = []
            if menu.show_back and menu.parent_menu:
                nav_options.append("b) Back")
            if menu.show_quit:
                nav_options.append("q) Quit")
            
            if nav_options:
                print("Navigation:")
                for nav_option in nav_options:
                    print(f"  {nav_option}")
                print()
            
            # Get user choice
            try:
                choice = input(f"{self.chars['arrow_right']} Select option: ").strip().lower()
                
                if not choice:
                    continue
                
                # Handle navigation
                if choice == 'q' and menu.show_quit:
                    return None
                elif choice == 'b' and menu.show_back and menu.parent_menu:
                    return 'back'
                
                # Find matching option
                selected_option = None
                for option in enabled_options:
                    if option.key.lower() == choice:
                        selected_option = option
                        break
                
                if not selected_option:
                    self.print_error(f"Invalid option: {choice}")
                    input("Press Enter to continue...")
                    continue
                
                # Execute action or show submenu
                if selected_option.submenu:
                    selected_option.submenu.parent_menu = menu
                    result = self.display_menu(selected_option.submenu)
                    if result != 'back':
                        return result
                elif selected_option.action:
                    try:
                        result = selected_option.action()
                        if result is not None:
                            return result
                    except Exception as e:
                        self.print_error(f"Action failed: {e}")
                        input("Press Enter to continue...")
                else:
                    return selected_option.key
                    
            except (KeyboardInterrupt, EOFError):
                return None
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Display confirmation dialog."""
        default_text = "Y/n" if default else "y/N"
        
        while True:
            try:
                choice = input(f"{self.chars['question']} {message} ({default_text}): ").strip().lower()
                
                if not choice:
                    return default
                elif choice in ['y', 'yes']:
                    return True
                elif choice in ['n', 'no']:
                    return False
                else:
                    self.print_error("Please enter 'y' for yes or 'n' for no")
                    
            except (KeyboardInterrupt, EOFError):
                return False
    
    def display_table(self, headers: List[str], rows: List[List[str]], 
                     title: Optional[str] = None) -> None:
        """Display formatted table."""
        if not rows:
            self.print_info("No data to display")
            return
        
        if title:
            print(self._colorize(title, 'bold'))
            print()
        
        # Calculate column widths
        col_widths = []
        all_rows = [headers] + rows
        
        for col_idx in range(len(headers)):
            max_width = max(len(str(row[col_idx])) for row in all_rows if col_idx < len(row))
            col_widths.append(min(max_width + 2, 40))  # Cap at 40 chars
        
        # Print header
        header_line = "│"
        separator_line = "├"
        
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            header_text = str(header)[:width-2].ljust(width-2)
            header_line += f" {header_text} │"
            separator_line += "─" * width + "┤" if i < len(headers)-1 else "─" * width + "┤"
        
        # Table borders
        top_border = "┌" + "┬".join("─" * width for width in col_widths) + "┐"
        bottom_border = "└" + "┴".join("─" * width for width in col_widths) + "┘"
        
        print(top_border)
        print(self._colorize(header_line, 'bold'))
        print(separator_line)
        
        # Print rows
        for row in rows:
            row_line = "│"
            for i, (cell, width) in enumerate(zip(row, col_widths)):
                cell_text = str(cell)[:width-2].ljust(width-2)
                row_line += f" {cell_text} │"
            print(row_line)
        
        print(bottom_border)
    
    def display_progress_with_steps(self, steps: List[str], current_step: int) -> None:
        """Display step-by-step progress."""
        print(self._colorize("Progress Steps:", 'bold'))
        print()
        
        for i, step in enumerate(steps):
            if i < current_step:
                icon = self._colorize(self.chars['check'], 'success')
                status = self._colorize("COMPLETED", 'success')
            elif i == current_step:
                icon = self._colorize(self.chars['arrow_right'], 'warning')
                status = self._colorize("IN PROGRESS", 'warning')
            else:
                icon = self._colorize(self.chars['bullet'], 'dim')
                status = self._colorize("PENDING", 'dim')
            
            print(f"  {icon} {step:<40} {status}")
        print()
    
    def wait_for_key(self, message: str = "Press any key to continue...") -> str:
        """Wait for single key press."""
        print(message, end='', flush=True)
        
        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            
            # Read single character
            key = sys.stdin.read(1)
            
            print()  # New line after key press
            return key
            
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def create_loading_animation(self, message: str = "Loading") -> 'LoadingAnimation':
        """Create loading animation context manager."""
        return LoadingAnimation(message, self)
    
    def create_progress_context(self, total: int, description: str = "Processing") -> 'ProgressContext':
        """Create progress tracking context manager."""
        return ProgressContext(total, description, self)


class LoadingAnimation:
    """Loading animation context manager."""
    
    def __init__(self, message: str, interface: InteractiveInterface):
        self.message = message
        self.interface = interface
        self.stop_animation = False
        self.animation_thread: Optional[threading.Thread] = None
    
    def __enter__(self):
        import threading
        self.animation_thread = threading.Thread(target=self._animate, daemon=True)
        self.animation_thread.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_animation = True
        if self.animation_thread:
            self.animation_thread.join(timeout=0.5)
        print()  # New line after animation
    
    def _animate(self):
        """Run loading animation."""
        import threading
        
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        
        while not self.stop_animation:
            print(f"\r{spinner[i % len(spinner)]} {self.message}", end='', flush=True)
            time.sleep(0.1)
            i += 1


class ProgressContext:
    """Progress tracking context manager."""
    
    def __init__(self, total: int, description: str, interface: InteractiveInterface):
        self.total = total
        self.description = description
        self.interface = interface
        self.current = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Successful completion
            self.update(self.total, "Complete")
    
    def update(self, current: int, status: Optional[str] = None):
        """Update progress."""
        self.current = current
        percentage = (current / self.total) * 100 if self.total > 0 else 0
        
        # Create progress bar
        bar_width = 40
        filled_width = int((percentage / 100) * bar_width)
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        status_text = f" - {status}" if status else ""
        progress_line = f"\r{self.description} |{bar}| {percentage:5.1f}% ({current}/{self.total}){status_text}"
        
        print(progress_line, end='', flush=True)
        
        if current >= self.total:
            print()  # New line when complete