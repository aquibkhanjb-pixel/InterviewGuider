from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100))
    industry = Column(String(50))
    size = Column(String(20))  # startup, medium, large
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    experiences = relationship("InterviewExperience", back_populates="company", cascade="all, delete-orphan")
    insights = relationship("CompanyInsight", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company(name='{self.name}')>"

class InterviewExperience(db.Model):
    __tablename__ = 'interview_experiences'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    
    # Content
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    
    # Source information
    source_url = Column(Text, unique=True, index=True)
    source_platform = Column(String(50), nullable=False, index=True)
    
    # Interview details
    role = Column(String(100), index=True)
    level = Column(String(20))
    location = Column(String(100))
    interview_date = Column(DateTime)
    experience_date = Column(DateTime, nullable=False, index=True)
    
    # Analysis results
    time_weight = Column(Float, default=1.0)
    sentiment_score = Column(Float)
    difficulty_score = Column(Float)
    success = Column(Boolean)
    
    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, index=True)
    
    # Relationships
    company = relationship("Company", back_populates="experiences")
    topic_mentions = relationship("TopicMention", back_populates="experience", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<InterviewExperience(company='{self.company.name if self.company else 'Unknown'}')>"

class Topic(db.Model):
    __tablename__ = 'topics'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    subcategory = Column(String(50))
    description = Column(Text)
    difficulty_level = Column(String(20))
    
    # Practice resources
    leetcode_tag = Column(String(50))
    practice_problems = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    mentions = relationship("TopicMention", back_populates="topic", cascade="all, delete-orphan")
    insights = relationship("CompanyInsight", back_populates="topic", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Topic(name='{self.name}')>"

class TopicMention(db.Model):
    __tablename__ = 'topic_mentions'
    
    id = Column(Integer, primary_key=True)
    experience_id = Column(Integer, ForeignKey('interview_experiences.id'), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False, index=True)
    
    # Analysis results
    frequency = Column(Integer, default=1)
    importance_score = Column(Float, default=0.0)
    context = Column(Text)
    confidence = Column(Float, default=0.5)
    
    # Metadata
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    experience = relationship("InterviewExperience", back_populates="topic_mentions")
    topic = relationship("Topic", back_populates="mentions")
    
    def __repr__(self):
        return f"<TopicMention(topic='{self.topic.name if self.topic else 'Unknown'}')>"

class AnalysisJob(db.Model):
    """Persisted job store so any gunicorn worker can read any job's status."""
    __tablename__ = 'analysis_jobs'

    id = Column(String(12), primary_key=True)
    company = Column(String(100), nullable=False)
    status = Column(String(20), default='queued', nullable=False, index=True)
    error = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AnalysisJob(id='{self.id}', status='{self.status}')>"


class CompanyInsight(db.Model):
    __tablename__ = 'company_insights'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False, index=True)
    
    # Analysis results
    role = Column(String(100), index=True)
    raw_frequency = Column(Float, default=0.0)
    weighted_frequency = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)
    sample_size = Column(Integer, default=0)
    
    # Trend analysis
    trend_direction = Column(String(10))
    trend_strength = Column(Float, default=0.0)
    seasonal_pattern = Column(Text)
    
    # Recommendations
    priority_level = Column(String(20), default='low', index=True)
    study_recommendation = Column(Text)
    practice_problems = Column(Text)
    
    # Metadata
    analysis_date = Column(DateTime, default=datetime.utcnow, index=True)
    data_freshness = Column(DateTime)
    
    # Relationships
    company = relationship("Company", back_populates="insights")
    topic = relationship("Topic", back_populates="insights")
    
    def __repr__(self):
        return f"<CompanyInsight(company='{self.company.name if self.company else 'Unknown'}')>"
