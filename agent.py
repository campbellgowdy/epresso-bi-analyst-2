"""Assistant: a dispatcher plus a router.
The router (rules now, a language model later) only CHOOSES a tool and its
arguments. Our code RUNS the tool. Nothing here executes model-written code."""
from __future__ import annotations

import analytics
from analytics import ToolResult

# The ONLY things the assistant may do. Add your own tools here.
TOOLS = {
    'get_total': {
        'fn': analytics.get_total,
        'params': {'value_col', 'filters'},
        'description': 'Sum a numeric column, optionally filtered.',
    },
    'group_total': {
        'fn': analytics.group_total,
        'params': {'value_col', 'group_col', 'filters'},
        'description': 'Sum a numeric column by group (store, channel, year, ...).',
    },
    'data_quality_report': {
        'fn': analytics.data_quality_report,
        'params': set(),
        'description': 'Report duplicates and missing values in the loaded data.',
    },
}

UNSUPPORTED = ('I can only answer questions that my approved analytical functions can '
               'calculate from the loaded data: ' + ', '.join(TOOLS) + '. '
               'I cannot answer that one.')

# For when you add a language model: keep these rules in the system prompt.
SYSTEM_PROMPT = """You are an analytical assistant for E-Presso managers.
Rules:
- Only state numbers that appear in a tool result. Never estimate or recall figures.
- Always call a tool before making a numerical claim.
- State the scope (which filters/period) of every answer.
- Separate Findings (from tool results), Interpretation, and Next steps.
- Revenue is not profit. Association is not causation.
- If the data cannot support a conclusion, say so and name the missing information.
- Never ask for, run, or write code. Never modify data."""


def run_tool(name: str, args: dict, df, log: list) -> ToolResult:
    """The dispatcher: validate the request, run the function, log the call."""
    if name not in TOOLS:
        result = analytics._error(name, f'Unknown tool: {name}')
    else:
        unexpected = set(args) - TOOLS[name]['params']
        if unexpected:
            result = analytics._error(name, f'Unexpected argument(s): {sorted(unexpected)}')
        else:
            result = TOOLS[name]['fn'](df, **args)
    log.append({'tool': name, 'arguments': args, 'result': result.to_dict()})
    return result


def rules_router(question: str, df):
    """Choose an approved analytical tool based on the question."""
    q = question.lower()

    # Data quality questions
    if any(w in q for w in ('missing', 'duplicate', 'quality', 'blank')):
        return 'data_quality_report', {}

    # Total revenue questions
    if any(w in q for w in ('total revenue', 'revenue total', 'sum of revenue')) and 'category' not in q and 'store type' not in q:
        if 'Revenue' in df.columns:
            return 'get_total', {'value_col': 'Revenue'}
        return None

    # Revenue by category
    if 'revenue' in q and 'category' in q:
        if 'Revenue' in df.columns:
            if 'Category' in df.columns:
                group_col = 'Category'
            elif 'Category ID' in df.columns:
                group_col = 'Category ID'
            else:
                return None

            return 'group_total', {
                'value_col': 'Revenue',
                'group_col': group_col
            }

    # Revenue by store type
    if 'revenue' in q and 'store type' in q:
        if 'Revenue' in df.columns and 'StoreType' in df.columns:
            return 'group_total', {
                'value_col': 'Revenue',
                'group_col': 'StoreType'
            }

    return None


def llm_router(question: str, df):
    """Option A router. TODO: after the rules-based version works, ask a model that
    supports function calling to choose from TOOLS. Return (name, args) or None."""
    raise NotImplementedError('Add the language-model router after your tools are tested.')


def format_findings(result: ToolResult) -> str:
    if result.error:
        return f'The request could not be completed: {result.error}'

    if result.tool == 'get_total':
        return f"Sum of Revenue: ${result.value:,.2f}"

    if result.tool == 'group_total':
        lines = ["Revenue by group:"]
        for group, amount in sorted(
            result.value.items(),
            key=lambda item: item[1],
            reverse=True
        ):
            lines.append(f"- {group}: ${amount:,.2f}")
        return "\n".join(lines)

    if result.tool == 'data_quality_report':
        return (
            f"Records reviewed: {result.value['rows']:,}\n"
            f"Duplicate rows: {result.value['duplicate_rows']:,}\n"
            f"Columns with missing information: "
            f"{len(result.value['columns_with_missing'])}"
        )

    return f'{result.definition}: {result.value}'


def answer_question(question: str, df, mode: str = 'rules') -> dict:
    log: list = []
    routed = rules_router(question, df) if mode == 'rules' else llm_router(question, df)
    if routed is None:
        return {'scope': 'n/a', 'findings': UNSUPPORTED, 'interpretation': '',
                'next_steps': '', 'tool_log': log}
    name, args = routed
    result = run_tool(name, args, df, log)
    return {
        'scope': str(result.scope),
        'findings': format_findings(result),
        'interpretation': ' '.join(result.caveats),
        'next_steps': '',
        'tool_log': log,
    }
