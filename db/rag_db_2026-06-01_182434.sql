--
-- PostgreSQL database dump
--

\restrict XgAKmPlwBjWYXuQpcZ0JyPyN7MZKdS9OJle2uMTge0b6Zbw23i7yhH0MEO9LvhR

-- Dumped from database version 16.14 (Homebrew)
-- Dumped by pg_dump version 16.14 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: gaan
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO gaan;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: rag_vectors_512; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rag_vectors_512 (
    id text NOT NULL,
    text text,
    metadata jsonb,
    embedding public.vector(512)
);


ALTER TABLE public.rag_vectors_512 OWNER TO postgres;

--
-- Name: rag_vectors_512 rag_vectors_512_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rag_vectors_512
    ADD CONSTRAINT rag_vectors_512_pkey PRIMARY KEY (id);


--
-- Name: rag_vectors_512_embedding_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX rag_vectors_512_embedding_idx ON public.rag_vectors_512 USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: gaan
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict XgAKmPlwBjWYXuQpcZ0JyPyN7MZKdS9OJle2uMTge0b6Zbw23i7yhH0MEO9LvhR

