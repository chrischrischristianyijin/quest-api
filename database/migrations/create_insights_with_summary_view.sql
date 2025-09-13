-- 创建insights_with_summary视图，合并insights和insight_contents表的数据
CREATE OR REPLACE VIEW insights_with_summary AS
SELECT 
    i.id,
    i.user_id,
    i.title,
    i.description,
    i.url,
    i.image_url,
    i.thought,
    i.meta,
    i.stack_id,
    i.created_at,
    i.updated_at,
    ic.summary,
    ic.text as content_text,
    ic.markdown,
    ic.content_type,
    ic.extracted_at,
    ic.thought as content_thought
FROM insights i
LEFT JOIN insight_contents ic ON i.id = ic.insight_id;

-- 添加注释
COMMENT ON VIEW insights_with_summary IS 'Insights视图，包含summary和content信息，用于RAG检索和API响应';

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_insights_with_summary_user_id ON insights(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_with_summary_created_at ON insights(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_insight_contents_insight_id ON insight_contents(insight_id);
