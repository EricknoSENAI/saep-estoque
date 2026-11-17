-- Script de criação e população do banco saep_db (MySQL 8)
DROP DATABASE IF EXISTS saep_db;
CREATE DATABASE saep_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE saep_db;

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  senha CHAR(64) NOT NULL            -- SHA-256 em hexadecimal
);

CREATE TABLE categorias (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE produtos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  marca VARCHAR(60) NOT NULL,
  categoria_id INT NOT NULL,
  especificacoes VARCHAR(255),       -- layout, conexão, DPI, versão HDMI etc.
  voltagem VARCHAR(20),
  garantia_meses INT NOT NULL DEFAULT 12,
  estoque_atual INT NOT NULL DEFAULT 0,
  estoque_minimo INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_prod_cat FOREIGN KEY (categoria_id) REFERENCES categorias(id),
  CONSTRAINT ck_estoque CHECK (estoque_atual >= 0 AND estoque_minimo >= 0)
);

CREATE TABLE movimentacoes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  produto_id INT NOT NULL,
  usuario_id INT NOT NULL,
  tipo ENUM('entrada','saida') NOT NULL,
  quantidade INT NOT NULL CHECK (quantidade > 0),
  data_movimentacao DATE NOT NULL,
  observacao VARCHAR(200),
  CONSTRAINT fk_mov_prod FOREIGN KEY (produto_id) REFERENCES produtos(id),
  CONSTRAINT fk_mov_user FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

INSERT INTO usuarios (nome, email, senha) VALUES
 ('Ana Estoquista',  'ana@loja.com',    SHA2('123456',256)),
 ('Bruno Silva',     'bruno@loja.com',  SHA2('123456',256)),
 ('Carla Gerente',   'carla@loja.com',  SHA2('123456',256));

INSERT INTO categorias (nome) VALUES
 ('Teclado'),('Mouse'),('Headset'),('Cabo'),('Fonte');

INSERT INTO produtos (nome, marca, categoria_id, especificacoes, voltagem, garantia_meses, estoque_atual, estoque_minimo) VALUES
 ('Teclado Mecânico K550',  'Redragon', 1, 'ABNT2 · com fio USB · mecânico',          NULL,     12, 14, 10),
 ('Teclado Sem Fio K380',   'Logitech', 1, 'US · Bluetooth · membrana',               NULL,     12,  8, 10),
 ('Mouse Gamer M720',       'Logitech', 2, 'Sem fio · 16000 DPI · ambidestro',        NULL,     12, 20, 15),
 ('Mouse Óptico M90',       'Multilaser',2,'Com fio · 1200 DPI · destro',             NULL,      6, 30, 15),
 ('Headset H110',           'HyperX',   3, 'USB · microfone removível',               NULL,     12,  9,  8),
 ('Cabo HDMI 2.0 3 m',      'Elg',      4, 'Versão 2.0 · 3 m',                        NULL,      3, 25, 20),
 ('Fonte ATX 650 W',        'Corsair',  5, '650 W · 80 Plus · bivolt',                'Bivolt', 24,  6,  5);

INSERT INTO movimentacoes (produto_id, usuario_id, tipo, quantidade, data_movimentacao, observacao) VALUES
 (1, 1, 'entrada', 20, '2026-11-03', 'Compra fornecedor'),
 (2, 2, 'saida',    4, '2026-11-05', 'Venda balcão'),
 (7, 1, 'saida',    2, '2026-11-10', 'Venda empresa'),
 (5, 3, 'entrada', 10, '2026-11-12', 'Reposição');
