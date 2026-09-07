from datetime import datetime
from sqlalchemy import (Column, Integer, String, Text, Float, DateTime,
                        ForeignKey, UniqueConstraint, Index, JSON)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Drama(Base):
    """一部剧的跨平台合并记录；同名剧在不同平台合并到同一条。"""
    __tablename__ = "drama"
    id = Column(Integer, primary_key=True)
    norm_title = Column(String(200), unique=True, index=True)  # 归一化标题，去重主键
    title = Column(String(200))
    synopsis = Column(Text, default="")
    cover = Column(String(500), default="")
    producer = Column(String(200), default="")
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # LLM 打标结果
    genre = Column(String(50), index=True)
    sub_genre = Column(String(100))
    hook_type = Column(String(50))
    audience = Column(String(20))
    era = Column(String(30))
    tags = Column(JSON, default=list)          # 爽点标签列表
    tag_reason = Column(Text, default="")
    tagged_at = Column(DateTime)

    cluster_id = Column(Integer, index=True)   # 聚类发现的簇

    snapshots = relationship("MetricSnapshot", back_populates="drama", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="drama", cascade="all, delete-orphan")
    listings = relationship("PlatformListing", back_populates="drama", cascade="all, delete-orphan")


class PlatformListing(Base):
    """某平台上这部剧的页面信息（同一部剧可有多条）。"""
    __tablename__ = "platform_listing"
    id = Column(Integer, primary_key=True)
    drama_id = Column(Integer, ForeignKey("drama.id"), index=True)
    platform = Column(String(50), index=True)
    platform_id = Column(String(200))
    url = Column(String(500))
    raw_tags = Column(JSON, default=list)      # 平台自带标签
    __table_args__ = (UniqueConstraint("platform", "platform_id", name="uq_platform_item"),)
    drama = relationship("Drama", back_populates="listings")


class MetricSnapshot(Base):
    """时间序列指标，每次采集写一行，趋势图从这里出。"""
    __tablename__ = "metric_snapshot"
    id = Column(Integer, primary_key=True)
    drama_id = Column(Integer, ForeignKey("drama.id"), index=True)
    platform = Column(String(50))
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    rank = Column(Integer)
    heat = Column(Float)          # 平台热度值/播放量，口径按平台
    likes = Column(Integer)
    comments_cnt = Column(Integer)
    drama = relationship("Drama", back_populates="snapshots")
    __table_args__ = (Index("ix_snapshot_drama_ts", "drama_id", "ts"),)


class Comment(Base):
    __tablename__ = "comment"
    id = Column(Integer, primary_key=True)
    drama_id = Column(Integer, ForeignKey("drama.id"), index=True)
    platform = Column(String(50))
    text = Column(Text)
    likes = Column(Integer, default=0)
    ts = Column(DateTime, default=datetime.utcnow)
    sentiment = Column(String(10))    # pos / neg / neu
    complaint_tag = Column(String(50))  # 差评的吐槽点，如"套路老"、"演技差"、"节奏慢"
    drama = relationship("Drama", back_populates="comments")


class Cluster(Base):
    """embedding 聚类出来的簇，LLM 给它起名。"""
    __tablename__ = "cluster"
    id = Column(Integer, primary_key=True)
    week = Column(String(10), index=True)     # 2026-W36
    label = Column(String(100))
    description = Column(Text)
    size = Column(Integer)
    keywords = Column(JSON, default=list)
    is_new = Column(Integer, default=0)       # 上一周没出现过的簇


class Report(Base):
    """LLM 生成的趋势周报。"""
    __tablename__ = "report"
    id = Column(Integer, primary_key=True)
    week = Column(String(10), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    content_md = Column(Text)
    content_json = Column(JSON)        # 结构化周报，站点渲染成卡片
    model = Column(String(100))
