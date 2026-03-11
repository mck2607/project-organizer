# this file is mainly to create the database tables.
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Boolean, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from datetime import datetime
from credentials import database as db

class Base(DeclarativeBase):
    pass

# ---------------- Project Data ----------------
class ProjectData(Base):
    __tablename__ = db.project_data

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(Text)
    project_estimated_date_time = Column(String(100),nullable=True)
    project_expected_date_time = Column(String(100),nullable=True)
    project_start_date_time = Column(String(100), nullable=True)
    frequency_type = Column(String(100))
    platform_type = Column(String(100))
    project_key_points = Column(Text, nullable=True)
    document_file = Column(Text, nullable=True)
    videos = Column(Text, nullable=True)
    project_created_date = Column(String(100))
    status = Column(String(100), default="pending")
    project_state = Column(String(20), default="old")


# ---------------- Project Master ----------------
class ProjectMaster(Base):
    __tablename__ = db.project_master_table

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(Text)
    project_estimated_date_time = Column(String(100))
    project_expected_date_time = Column(String(100))
    frequency_type = Column(String(100))
    platform_type = Column(String(100))
    project_key_points = Column(Text, nullable=True)
    document_file = Column(Text, nullable=True)
    videos = Column(Text, nullable=True)
    project_created_date = Column(String(100))
    status = Column(String(200), default="pending")
    project_state = Column(String(20), default="new")


# ---------------- Project Assignment ----------------
class ProjectAssignment(Base):
    __tablename__ = db.project_assignment_table

    project_id = Column(Integer, primary_key=True)
    project_name = Column(Text)
    task_detail = Column(Text, nullable=True)
    project_progress = Column(String(200), default="0")
    assigned_person_name = Column(Text)
    assigned_person_email = Column(String(300))
    assigned_person_username = Column(String(100), primary_key=True)
    assigned_person_position = Column(String(100))
    project_assigner_position = Column(String(400))
    project_assigner_name = Column(Text)
    project_assigner_email = Column(String(300))
    person_assigner_username = Column(String(200))
    assigning_date = Column(String(100))
    last_activity_date = Column(String(100), nullable=True)
    code_uploaded = Column(String(10), nullable=True, default='false')
    project_delay_in_minutes = Column(String(200), default="0")
    qa_iteration_count = Column(Integer, default=-1)

    __table_args__ = (
        UniqueConstraint("project_id", "assigned_person_username", name="unique_dev_project"),
    )


# ---------------- Project Codebase ----------------
class ProjectCodebase(Base):
    __tablename__ = db.project_codebase

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_submit_person_username = Column(String(100))
    code_submit_person_name = Column(Text)
    codebase_submit_date = Column(String(100))
    code_file = Column(Text)
    project_id = Column(Integer)
    project_name = Column(Text)
    task_detail = Column(Text)


# ---------------- Employee ----------------
class Employee(Base):
    __tablename__ = db.employee_table

    username = Column(String(100), primary_key=True)
    email = Column(String(500))
    name = Column(Text)
    date_joined = Column(String(100), nullable=True)
    profile_image = Column(String(700), nullable=True)
    position = Column(String(400))
    phone = Column(String(20))
    department = Column(String(50))
    password = Column(String(700))
    reporting_person_name = Column(Text, nullable=True)
    reporting_person_email = Column(String(500), nullable=True)
    reporting_person_position = Column(String(400), nullable=True)
    reporting_person_username = Column(String(100), nullable=True)
    access_level = Column(String(10))
    post_access = Column(Boolean)


# ---------------- Login Log ----------------
class LoginLog(Base):
    __tablename__ = db.login_log_table

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100))
    name = Column(Text)
    login_time = Column(String(100))
    logout_time = Column(String(100), default="N/A")
    position = Column(String(400))
    ip_address = Column(String(10), nullable=True)


# ---------------- Project Updates ----------------
class ProjectUpdates(Base):
    __tablename__ = db.project_updates_table

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    project_name = Column(Text, nullable=False)
    sender_username = Column(String(100))
    sender_name = Column(Text)
    text = Column(Text)
    images = Column(Text)
    type_of_text = Column(String(50))
    created_at = Column(String(100))
    department = Column(String(100))


# ---------------- Todo Master ----------------
class TodoMaster(Base):
    __tablename__ = db.todo_master_table

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer)
    project_name = Column(Text)
    todo_title = Column(Text)
    todo_descr = Column(Text)
    priority = Column(Text)
    status = Column(String(100))
    created_by = Column(String(200))
    color = Column(String(200))
    created_at = Column(String(100))


# ---------------- Todo Assignment ----------------
class TodoAssignment(Base):
    __tablename__ = db.todo_assignment_table

    id = Column(Integer, primary_key=True, autoincrement=True)
    todo_id = Column(Integer)
    project_id = Column(Integer)
    project_name = Column(Text)
    created_by_username = Column(String(100))
    created_by_name = Column(Text)
    assignee_name = Column(Text)
    assignee_username = Column(Text)
    reporting_person_username = Column(String(100))
    todo_created_date = Column(String(100))
    todo_completed_date = Column(String(100))
    status = Column(String(100))
    show_or_not = Column(Boolean, default=True)
    access_level = Column(String(100))


# ---------------- Todo Escalation ----------------
class TodoEscalation(Base):
    __tablename__ = db.todo_esclation_table

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_by_username = Column(String(100))
    created_by_name = Column(Text)
    todo_id = Column(Integer)
    project_id = Column(Integer)
    project_name = Column(Text)
    assignee_name = Column(String(100))
    assignee_username = Column(Text)
    todo_created_date = Column(String(100))
    todo_completed_date = Column(String(100))
    status = Column(String(100))
    show_or_not = Column(Boolean, default=True)
    is_started = Column(Boolean, default=False)
    responses = Column(Text)  # JSON string to store multiple responses
    response_updated_at = Column(String(100))  # Last response update timestamp
    access_level = Column(String(100))



# ------------------------------------------------------------
class KnowledgePost(Base):
    __tablename__ = "knowledge_posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), index=True)
    author_username = Column(String(100), ForeignKey(f"{db.employee_table}.username"), nullable=False)
    author = Column(Text, nullable=False)
    downloads = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # CORRECT relationship definitions - remove lazy='selectinload'
    files = relationship("PostFile", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    feedbacks = relationship("PostFeedback", back_populates="post", cascade="all, delete-orphan")

class PostFile(Base):
    __tablename__ = "post_files"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("knowledge_posts.id", ondelete="CASCADE"))
    file_name = Column(String(255))
    file_path = Column(String(500))
    file_type = Column(String(100))
    file_size = Column(Integer)

    post = relationship("KnowledgePost", back_populates="files")

class PostFeedback(Base):
    __tablename__ = "post_feedbacks"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("knowledge_posts.id", ondelete="CASCADE"))
    author_username = Column(String(100), ForeignKey(f"{db.employee_table}.username"))
    author = Column(Text)
    text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post = relationship("KnowledgePost", back_populates="feedbacks")


class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("knowledge_posts.id", ondelete="CASCADE"))
    author_username = Column(String(100), ForeignKey(f"{db.employee_table}.username"))
    author = Column(Text)
    post = relationship("KnowledgePost", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("post_id", "author_username", name="uq_post_like"),
    )


#___________________________________
class QAPosts(Base):
    __tablename__ = "qa_posts"

    id = Column(Integer, primary_key=True)
    project_name = Column(Text, nullable=False, index=True)
    project_id = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    frequency = Column(String(100))
    task_details = Column(Text)
    author_username = Column(String(100), ForeignKey(f"{db.employee_table}.username"), nullable=False)
    author = Column(Text, nullable=False)
    downloads = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    qa_files = relationship(
        "QAFiles",
        back_populates="post",
        cascade="all, delete-orphan"
    )

    qa_feedbacks = relationship(
        "QAFeedback",
        back_populates="post",
        cascade="all, delete-orphan"
    )


class QAFiles(Base):
    __tablename__ = "qa_files"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("qa_posts.id", ondelete="CASCADE"))
    file_name = Column(String(255))
    file_path = Column(String(500))
    file_type = Column(String(100))
    file_size = Column(Integer)

    post = relationship("QAPosts", back_populates="qa_files")

class QAFeedback(Base):
    __tablename__ = "qa_feedbacks"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("qa_posts.id", ondelete="CASCADE"))
    author_username = Column(String(100), ForeignKey(f"{db.employee_table}.username"))
    author = Column(Text)
    text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post = relationship("QAPosts", back_populates="qa_feedbacks")



class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    # receiver
    user_id = Column(String(255), index=True)
    # sender info
    sender_id = Column(String(255), nullable=True)
    sender_name = Column(String, nullable=True)
    type = Column(String(255), nullable=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())