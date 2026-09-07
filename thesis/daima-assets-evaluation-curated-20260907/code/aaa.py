import matplotlib.pyplot as plt
import matplotlib.patches as patches
import textwrap

def draw_result_comparison(cases, filename="result_comparison.png"):
    # === 布局设置 ===
    # 宽度比例: 视频区域(30%) + 问答区域(70%)
    fig_width = 20
    # 根据内容动态计算高度
    total_height_units = sum([len(c['qas']) * 12 + 4 for c in cases]) 
    fig_height = max(12, total_height_units * 0.4) 
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100 * len(cases)) # 归一化坐标系
    ax.axis('off')
    
    # === 配色方案 (学术风格) ===
    colors = {
        'video_bg': "#e0e0e0",     # 视频占位符背景
        'video_border': "#9e9e9e",
        'q_bg': "#e3f2fd",         # 问题背景 (浅蓝)
        'q_text': "#0d47a1",
        'ours_bg': "#e8f5e9",      # Ours背景 (浅绿)
        'ours_border': "#2e7d32",  # Ours边框 (深绿)
        'base_bg': "#fafafa",      # Baseline背景 (灰白)
        'base_border': "#bdbdbd",
        'gt_bg': "#fff8e1",        # GT背景 (浅黄)
        'gt_text': "#f57f17"
    }
    
    # 从上往下绘制
    current_y = 100 * len(cases) - 5
    section_height = 100 # 每个Case占用的垂直单位
    
    for i, case in enumerate(cases):
        # --- 1. 左侧：视频区域 (Video Area) ---
        # 留出空白框，方便您贴图
        video_box_h = 40 
        video_box_w = 25
        video_x = 2
        video_y = current_y - video_box_h - 5
        
        rect_vid = patches.FancyBboxPatch((video_x, video_y), video_box_w, video_box_h,
                                        boxstyle="round,pad=1", linewidth=2, linestyle='--',
                                        edgecolor=colors['video_border'], facecolor=colors['video_bg'])
        ax.add_patch(rect_vid)
        
        # 视频标题/描述
        ax.text(video_x + video_box_w/2, video_y + video_box_h/2, 
                f"[Placeholder for]\n{case['title']}\n(Paste Screenshot Here)", 
                ha='center', va='center', fontsize=14, color="#757575", fontweight='bold')
        
        # --- 2. 右侧：问答区域 (QA Area) ---
        qa_x_start = 30
        qa_current_y = current_y - 2
        
        for qa in case['qas']:
            # A. 问题 (Question)
            q_text = "Q: " + qa['question']
            q_wrapped = "\n".join(textwrap.wrap(q_text, width=85))
            q_h = q_text.count('\n') * 2 + 6
            
            # 绘制问题背景条
            rect_q = patches.FancyBboxPatch((qa_x_start, qa_current_y - q_h), 68, q_h,
                                          boxstyle="round,pad=0.5", linewidth=0, 
                                          color=colors['q_bg'])
            ax.add_patch(rect_q)
            ax.text(qa_x_start + 1, qa_current_y - 2.5, q_wrapped, 
                    fontsize=13, fontweight='bold', color=colors['q_text'], va='top')
            
            qa_current_y -= (q_h + 3)
            
            # B. 对比回答 (Ours vs Baseline)
            # 准备文本
            ours_txt = "Ours: " + qa['ours']
            base_txt = "SOTA: " + qa['base']
            gt_txt = "GT: " + qa['gt']
            
            # 自动换行
            ours_wrapped = "\n".join(textwrap.wrap(ours_txt, width=90))
            base_wrapped = "\n".join(textwrap.wrap(base_txt, width=90))
            gt_wrapped = "\n".join(textwrap.wrap(gt_txt, width=90))
            
            # 计算各块高度
            h_o = ours_wrapped.count('\n') * 2.2 + 4
            h_b = base_wrapped.count('\n') * 2.2 + 4
            h_g = gt_wrapped.count('\n') * 2.2 + 4
            
            # 绘制 Ours (突出显示)
            rect_o = patches.FancyBboxPatch((qa_x_start, qa_current_y - h_o), 68, h_o,
                                          boxstyle="round,pad=0.5", linewidth=2, 
                                          edgecolor=colors['ours_border'], facecolor=colors['ours_bg'])
            ax.add_patch(rect_o)
            ax.text(qa_x_start + 1, qa_current_y - 2, ours_wrapped, 
                    fontsize=12, color="#1b5e20", va='top') # 深绿色字
            qa_current_y -= (h_o + 2)
            
            # 绘制 Baseline
            rect_b = patches.FancyBboxPatch((qa_x_start, qa_current_y - h_b), 68, h_b,
                                          boxstyle="round,pad=0.5", linewidth=1, 
                                          edgecolor=colors['base_border'], facecolor=colors['base_bg'])
            ax.add_patch(rect_b)
            ax.text(qa_x_start + 1, qa_current_y - 2, base_wrapped, 
                    fontsize=12, color="#616161", va='top')
            qa_current_y -= (h_b + 2)
            
            # 绘制 GT (紧凑)
            rect_g = patches.FancyBboxPatch((qa_x_start, qa_current_y - h_g), 68, h_g,
                                          boxstyle="round,pad=0.5", linewidth=0, 
                                          color=colors['gt_bg'])
            ax.add_patch(rect_g)
            ax.text(qa_x_start + 1, qa_current_y - 2, gt_wrapped, 
                    fontsize=11, fontstyle='italic', color=colors['gt_text'], va='top')
            
            qa_current_y -= (h_g + 8) # 问题间距
            
        current_y -= section_height # Case间距

    plt.tight_layout()
    plt.savefig(filename, dpi=120, bbox_inches='tight')
    plt.close()

# === 数据 ===
cases_data = [
    {
        "title": "Video 1: BitPanda Ad\n(Fine-grained Visuals)",
        "qas": [
            {
                "question": "What visual element helps convey the idea of investing everyday pleasures?",
                "ours": "The smartphone screen displaying a coffee drink with a price tag of €2,000 and the hashtag #SocialDistance visually conveys the idea...",
                "base": "The smartphone app interface displaying drinks with price tags visually connects everyday pleasures...",
                "gt": "By showing familiar scenes like a movie night and linking them to investment opportunities."
            },
            {
                "question": "How does BitPanda encourage people to start investing?",
                "ours": "...highlights a low entry point (\"from €1\") and offers a 20 euro bonus for first-time investors...",
                "base": "BitPanda offers a 20€ bonus for first investments and promotes investing small amounts...",
                "gt": "By offering a bonus for the first investment made."
            }
        ]
    },
    {
        "title": "Video 2: Kiri Campaign\n(Audio-Visual Reasoning)",
        "qas": [
            {
                "question": "What role did technology play in the campaign's execution?",
                "ours": "...Viewers were invited to \"Share your messages\" on a smartphone interface, as shown by the visible typing screen and emojis...",
                "base": "The campaign utilized technology for people to submit and share personal thank-you messages digitally...",
                "gt": "Social media was used to collect messages from mothers for the boxes."
            }
        ]
    }
]

draw_result_comparison(cases_data, "result_comparison_v2.png")