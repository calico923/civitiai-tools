#!/usr/bin/env python3
"""
ReDoS (Regular Expression Denial of Service) Protection.
Implements timeout and safety mechanisms for regex operations.

Based on Gemini audit recommendation for security hardening.
"""

import re
import time
import threading
import signal
from typing import Pattern, List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReDoSRiskLevel(Enum):
    """Risk levels for regex patterns."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PatternAnalysis:
    """Analysis result for a regex pattern."""
    pattern: str
    risk_level: ReDoSRiskLevel
    issues: List[str]
    recommendations: List[str]
    max_safe_length: int = 1000


class TimeoutException(Exception):
    """Exception raised when regex operation times out."""
    pass


class ReDoSProtector:
    """
    Protects against ReDoS attacks by:
    1. Analyzing regex patterns for ReDoS vulnerabilities
    2. Implementing timeouts for regex operations
    3. Limiting input string length
    4. Providing safe alternatives for dangerous patterns
    """
    
    def __init__(self, default_timeout: float = 5.0, max_input_length: int = 10000):
        """
        Initialize ReDoS protector.
        
        Args:
            default_timeout: Default timeout for regex operations (seconds)
            max_input_length: Maximum allowed input string length
        """
        self.default_timeout = default_timeout
        self.max_input_length = max_input_length
        
        # Cache for pattern analysis
        self._pattern_cache: Dict[str, PatternAnalysis] = {}
        
        # Compiled safe patterns
        self._safe_patterns: Dict[str, Pattern] = {}
    
    def analyze_pattern(self, pattern: str) -> PatternAnalysis:
        """
        Analyze a regex pattern for ReDoS vulnerabilities.
        
        Args:
            pattern: Regular expression pattern to analyze
            
        Returns:
            PatternAnalysis with risk assessment
        """
        if pattern in self._pattern_cache:
            return self._pattern_cache[pattern]
        
        issues = []
        recommendations = []
        risk_level = ReDoSRiskLevel.SAFE
        max_safe_length = 10000
        
        # Check for nested quantifiers (most dangerous)
        nested_quantifiers = [
            r'\([^)]*[+*?]\)[+*?]',  # (a+)+ pattern
            r'\([^)]*[+*?][^)]*\)[+*?]',  # (a+b*)+ pattern
            r'[+*?][^|()]*[+*?]',  # a+.*+ pattern
        ]
        
        for nq_pattern in nested_quantifiers:
            if re.search(nq_pattern, pattern):
                issues.append("Nested quantifiers detected - high ReDoS risk")
                recommendations.append("Avoid nested quantifiers like (a+)+ or (a*)+")
                risk_level = ReDoSRiskLevel.CRITICAL
                max_safe_length = 100
                break
        
        # Check for alternation with overlapping patterns
        if '|' in pattern and any(q in pattern for q in ['+', '*', '?']):
            alternation_risk = self._analyze_alternation_risk(pattern)
            if alternation_risk:
                issues.append("Alternation with quantifiers - potential ReDoS risk")
                recommendations.append("Ensure alternation branches don't overlap")
                risk_level = max(risk_level, ReDoSRiskLevel.MEDIUM)
        
        # Check for excessive backtracking potential
        backtrack_patterns = [
            r'\.\*.*\.\*',  # .*.*
            r'\.\+.*\.\+',  # .+.+
            r'[^()]*[+*][^()]*[+*]',  # a*b* patterns
        ]
        
        for bt_pattern in backtrack_patterns:
            if re.search(bt_pattern, pattern):
                issues.append("Pattern may cause excessive backtracking")
                recommendations.append("Use possessive quantifiers or atomic groups")
                risk_level = max(risk_level, ReDoSRiskLevel.MEDIUM)
                max_safe_length = min(max_safe_length, 1000)
        
        # Check for repetition of groups
        if re.search(r'\([^)]+\)[+*?]\{', pattern):
            issues.append("Repetition of groups detected")
            recommendations.append("Consider unrolling loops or using non-capturing groups")
            risk_level = max(risk_level, ReDoSRiskLevel.HIGH)
            max_safe_length = min(max_safe_length, 500)
        
        # Create analysis result
        analysis = PatternAnalysis(
            pattern=pattern,
            risk_level=risk_level,
            issues=issues,
            recommendations=recommendations,
            max_safe_length=max_safe_length
        )
        
        # Cache result
        self._pattern_cache[pattern] = analysis
        return analysis
    
    def _analyze_alternation_risk(self, pattern: str) -> bool:
        """Check if alternation creates ReDoS risk."""
        # Simple heuristic: if alternation branches start with same pattern
        # and have quantifiers, it could cause exponential backtracking
        alternation_parts = pattern.split('|')
        if len(alternation_parts) < 2:
            return False
        
        # Check if multiple parts start with similar patterns
        starts = [part.strip()[:3] for part in alternation_parts if part.strip()]
        return len(set(starts)) < len(starts)
    
    def compile_safe_pattern(self, pattern: str, flags: int = 0) -> Pattern:
        """
        Compile a regex pattern with safety checks.
        
        Args:
            pattern: Regular expression pattern
            flags: Regex flags
            
        Returns:
            Compiled pattern
            
        Raises:
            ValueError: If pattern is too dangerous
        """
        analysis = self.analyze_pattern(pattern)
        
        if analysis.risk_level == ReDoSRiskLevel.CRITICAL:
            raise ValueError(f"Pattern rejected due to critical ReDoS risk: {pattern}")
        
        cache_key = f"{pattern}_{flags}"
        if cache_key in self._safe_patterns:
            return self._safe_patterns[cache_key]
        
        try:
            compiled_pattern = re.compile(pattern, flags)
            self._safe_patterns[cache_key] = compiled_pattern
            return compiled_pattern
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def safe_search(self, pattern: str, text: str, timeout: Optional[float] = None,
                   flags: int = 0) -> Optional[re.Match]:
        """
        Perform a safe regex search with timeout protection.
        
        Args:
            pattern: Regular expression pattern
            text: Text to search
            timeout: Operation timeout (uses default if None)
            flags: Regex flags
            
        Returns:
            Match object or None
            
        Raises:
            TimeoutException: If operation times out
            ValueError: If pattern or text is unsafe
        """
        timeout = timeout or self.default_timeout
        
        # Check input length
        if len(text) > self.max_input_length:
            raise ValueError(f"Input text too long: {len(text)} > {self.max_input_length}")
        
        # Analyze pattern
        analysis = self.analyze_pattern(pattern)
        
        if analysis.risk_level == ReDoSRiskLevel.CRITICAL:
            raise ValueError(f"Pattern rejected: {analysis.issues[0]}")
        
        # Limit text length based on pattern risk
        if len(text) > analysis.max_safe_length:
            logger.warning(f"Truncating text from {len(text)} to {analysis.max_safe_length} chars due to pattern risk")
            text = text[:analysis.max_safe_length]
        
        # Compile pattern
        compiled_pattern = self.compile_safe_pattern(pattern, flags)
        
        # Execute with timeout
        return self._execute_with_timeout(
            lambda: compiled_pattern.search(text),
            timeout
        )
    
    def safe_findall(self, pattern: str, text: str, timeout: Optional[float] = None,
                    flags: int = 0) -> List[str]:
        """
        Perform a safe regex findall with timeout protection.
        
        Args:
            pattern: Regular expression pattern
            text: Text to search
            timeout: Operation timeout
            flags: Regex flags
            
        Returns:
            List of matches
        """
        timeout = timeout or self.default_timeout
        
        # Similar safety checks as safe_search
        if len(text) > self.max_input_length:
            raise ValueError(f"Input text too long: {len(text)} > {self.max_input_length}")
        
        analysis = self.analyze_pattern(pattern)
        
        if analysis.risk_level == ReDoSRiskLevel.CRITICAL:
            raise ValueError(f"Pattern rejected: {analysis.issues[0]}")
        
        if len(text) > analysis.max_safe_length:
            text = text[:analysis.max_safe_length]
        
        compiled_pattern = self.compile_safe_pattern(pattern, flags)
        
        return self._execute_with_timeout(
            lambda: compiled_pattern.findall(text),
            timeout
        )
    
    def _execute_with_timeout(self, func, timeout: float):
        """Execute function with timeout using thread-based approach."""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # Thread is still running - timeout occurred
            # Note: We can't actually kill the thread in Python
            # 
            # FUTURE IMPROVEMENT (Gemini Recommendation):
            # For more robust ReDoS protection, consider using multiprocessing:
            #   - Execute regex in separate process instead of thread
            #   - Processes can be forcibly terminated, preventing CPU exhaustion
            #   - Example: multiprocessing.Process with terminate() method
            #   - Trade-off: Increased overhead for process creation/communication
            # 
            logger.warning("Regex operation timed out but thread may still be running")
            logger.warning("Consider multiprocessing for more robust timeout handling")
            raise TimeoutException(f"Regex operation timed out after {timeout} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def get_safe_alternatives(self, pattern: str) -> List[str]:
        """
        Suggest safe alternatives for dangerous regex patterns.
        
        Args:
            pattern: Original pattern
            
        Returns:
            List of safer alternative patterns
        """
        alternatives = []
        
        # Common ReDoS patterns and their safe alternatives
        safe_replacements = {
            r'\(\.\*\)\+': r'.*',  # (.*)+  ->  .*
            r'\(\.\+\)\+': r'.+',  # (.+)+  ->  .+
            r'\(a\*\)\*': r'a*',   # (a*)*  ->  a*
            r'\(a\+\)\+': r'a+',   # (a+)+  ->  a+
            r'\.\*\.\*': r'.*',    # .*.*   ->  .*
            r'\.\+\.\+': r'.+',    # .+.+   ->  .+
        }
        
        for dangerous, safe in safe_replacements.items():
            if re.search(dangerous, pattern, re.IGNORECASE):
                safer_pattern = re.sub(dangerous, safe, pattern, flags=re.IGNORECASE)
                alternatives.append(safer_pattern)
        
        # If no specific alternatives found, suggest general improvements
        if not alternatives:
            if any(char in pattern for char in ['+', '*']):
                alternatives.append("Consider using possessive quantifiers (++, *+)")
                alternatives.append("Consider using atomic groups (?>...)")
                alternatives.append("Consider limiting input length")
        
        return alternatives
    
    def audit_patterns(self, patterns: List[str]) -> Dict[str, PatternAnalysis]:
        """
        Audit a list of regex patterns for ReDoS vulnerabilities.
        
        Args:
            patterns: List of regex patterns to audit
            
        Returns:
            Dict mapping pattern to analysis result
        """
        results = {}
        
        for pattern in patterns:
            try:
                analysis = self.analyze_pattern(pattern)
                results[pattern] = analysis
                
                if analysis.risk_level in [ReDoSRiskLevel.HIGH, ReDoSRiskLevel.CRITICAL]:
                    logger.warning(f"High-risk pattern detected: {pattern}")
                    logger.warning(f"Issues: {', '.join(analysis.issues)}")
                    logger.warning(f"Recommendations: {', '.join(analysis.recommendations)}")
            
            except Exception as e:
                logger.error(f"Error analyzing pattern '{pattern}': {e}")
                results[pattern] = PatternAnalysis(
                    pattern=pattern,
                    risk_level=ReDoSRiskLevel.HIGH,
                    issues=[f"Analysis error: {e}"],
                    recommendations=["Manual review required"]
                )
        
        return results
    
    def generate_audit_report(self, patterns: List[str]) -> str:
        """
        Generate a comprehensive audit report for regex patterns.
        
        Args:
            patterns: List of patterns to audit
            
        Returns:
            Formatted audit report
        """
        results = self.audit_patterns(patterns)
        
        report_lines = [
            "# ReDoS Security Audit Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Patterns analyzed: {len(patterns)}",
            "",
            "## Summary",
        ]
        
        # Count by risk level
        risk_counts = {}
        for analysis in results.values():
            risk_level = analysis.risk_level
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        for risk_level in ReDoSRiskLevel:
            count = risk_counts.get(risk_level, 0)
            report_lines.append(f"- {risk_level.value.title()}: {count}")
        
        report_lines.extend([
            "",
            "## Detailed Results",
            ""
        ])
        
        # Detailed results
        for pattern, analysis in results.items():
            report_lines.extend([
                f"### Pattern: `{pattern}`",
                f"**Risk Level:** {analysis.risk_level.value.title()}",
                f"**Max Safe Length:** {analysis.max_safe_length}",
                ""
            ])
            
            if analysis.issues:
                report_lines.append("**Issues:**")
                for issue in analysis.issues:
                    report_lines.append(f"- {issue}")
                report_lines.append("")
            
            if analysis.recommendations:
                report_lines.append("**Recommendations:**")
                for rec in analysis.recommendations:
                    report_lines.append(f"- {rec}")
                report_lines.append("")
            
            alternatives = self.get_safe_alternatives(pattern)
            if alternatives:
                report_lines.append("**Safe Alternatives:**")
                for alt in alternatives:
                    report_lines.append(f"- `{alt}`")
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        return "\n".join(report_lines)


# Global instance for easy access
default_protector = ReDoSProtector()


def safe_search(pattern: str, text: str, timeout: float = 5.0, flags: int = 0) -> Optional[re.Match]:
    """Convenience function for safe regex search."""
    return default_protector.safe_search(pattern, text, timeout, flags)


def safe_findall(pattern: str, text: str, timeout: float = 5.0, flags: int = 0) -> List[str]:
    """Convenience function for safe regex findall."""
    return default_protector.safe_findall(pattern, text, timeout, flags)


def analyze_pattern(pattern: str) -> PatternAnalysis:
    """Convenience function for pattern analysis."""
    return default_protector.analyze_pattern(pattern)