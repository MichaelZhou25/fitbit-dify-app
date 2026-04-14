from __future__ import annotations

from .packets import ConsultPacket, LocalConsultReport


def build_local_report(packet: ConsultPacket) -> LocalConsultReport:
    risk = packet.risk
    quality = packet.quality
    risk_text = {
        "low": "当前窗口没有看到明显的高风险生理模式。",
        "medium": "当前窗口出现了中等强度的应激或焦虑相关生理变化。",
        "high": "当前窗口出现了较强的应激或焦虑相关生理变化。",
        "abstain": "当前信号质量不足，系统暂不建议做高置信判断。",
    }.get(risk.risk_level, "当前结果需要进一步核查。")

    if not quality.is_usable:
        evidence = "不足"
        next_actions = [
            "检查佩戴是否稳定，避免运动伪迹",
            "补采 3-5 分钟安静状态信号",
            "如有必要，补充简短问卷",
        ]
    elif risk.risk_level == "high":
        evidence = "较充分"
        next_actions = [
            "补充简短焦虑量表或症状追问",
            "复核最近睡眠、活动和压力事件",
            "若持续高风险或伴随明显不适，建议联系医生或支持者",
        ]
    elif risk.risk_level == "medium":
        evidence = "中等"
        next_actions = [
            "建议继续观察后续窗口趋势",
            "补充近期睡眠、活动和主观压力信息",
            "必要时追加量表评估",
        ]
    else:
        evidence = "较充分"
        next_actions = [
            "维持常规监测",
            "继续积累个体基线",
        ]

    triggers = "、".join(packet.rule_triggers) if packet.rule_triggers else "无明显规则触发项"
    features = "、".join(risk.top_features) if risk.top_features else "无"
    user_summary = (
        f"{risk_text} 风险等级为 {risk.risk_level}，证据{evidence}。"
        f" 当前数据质量为 {quality.overall_quality:.2f}，主要驱动特征包括 {features}。"
    )
    clinician_summary = (
        f"Risk={risk.risk_level} score={risk.risk_score:.2f} uncertainty={risk.uncertainty:.2f}; "
        f"quality={quality.overall_quality:.2f}; triggers={triggers}; top_features={features}."
    )
    return LocalConsultReport(
        user_summary=user_summary,
        clinician_summary=clinician_summary,
        next_actions=next_actions,
        evidence_sufficiency=evidence,
    )

