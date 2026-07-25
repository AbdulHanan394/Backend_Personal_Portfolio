class Knowledge(Base):
    __tablename__ = "knowledge"

    id = mapped_column(UUID, primary_key=True)

    source = mapped_column(String)
    type = mapped_column(String)

    title = mapped_column(String)

    content = mapped_column(Text)

    metadata = mapped_column(JSON)

    created_at = mapped_column(DateTime)