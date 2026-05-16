from datetime import datetime, date
from typing import Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

template_dir = Path(__file__).parent.parent / "frontend" / "templates"

env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=select_autoescape(['html', 'xml'])
)

def setup_jinja_env(app):
    from fastapi import Request
    
    def cents_to_dollars(value: int) -> str:
        if value is None:
            return "$0.00"
        return f"${abs(value) / 100:,.2f}"
    
    def format_date(value: date) -> str:
        if value is None:
            return ""
        return value.strftime("%b %d, %Y")
    
    def divide_by_100(value: int) -> str:
        if value is None:
            return "0"
        return f"{value / 100:.2f}"
    
    def capitalize(value: str) -> str:
        if value is None:
            return ""
        return value.capitalize()
    
    env.filters['cents_to_dollars'] = cents_to_dollars
    env.filters['format_date'] = format_date
    env.filters['divide_by_100'] = divide_by_100
    env.filters['capitalize'] = capitalize
    env.filters['string'] = str
    
    return env

def render_template(template_name: str, context: dict[str, Any]) -> str:
    template = env.get_template(template_name)
    return template.render(**context)