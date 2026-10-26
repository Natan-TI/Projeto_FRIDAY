/*
 * ==========================================================================
 *   PROJETO M.A.D.A.R.A. - Corpo do boneco (Arduino)
 * ==========================================================================
 *
 * Recebe comandos do Python (modulos/arduino.py) pela porta serial e
 * controla:
 *   - dois LEDs, que são os OLHOS do boneco;
 *   - um motor DC, ligado por uma ponte H, que gira a CABEÇA.
 *
 * Protocolo: um caractere por comando, a 9600 baud - mesmo formato do
 * 'arduino_serial.ino' do professor:
 *
 *   'O' -> acende os dois LEDs    'G' -> começa a girar a cabeça
 *   'o' -> apaga os dois LEDs     'P' -> para e volta a cabeça ao centro
 *   'V' -> só o LED vermelho      (Sharingan)
 *   'A' -> só o LED azul          (Rinnegan)
 *
 * Ligações (Arduino Uno):
 *   Ponte H  ENA : pino 3  (velocidade, por PWM)
 *   Ponte H  IN1 : pino 4  (sentido)
 *   Ponte H  IN2 : pino 5  (sentido)
 *   Motor        : OUT1 e OUT2 da ponte H
 *   LED vermelho : pino 9  -> resistor de 220 ohms -> LED -> GND
 *   LED azul     : pino 10 -> resistor de 220 ohms -> LED -> GND
 *
 * Os LEDs usam os pinos 9 e 10 porque precisam de PWM (analogWrite) para
 * acender gradualmente. No Uno só os pinos 3, 5, 6, 9, 10 e 11 têm PWM;
 * o 3 e o 5 já são da ponte H, e o 9 e o 10 usam o mesmo timer, então os
 * dois LEDs brilham exatamente na mesma frequência.
 *
 * Como a cabeça "vai e volta" com um motor DC:
 *   Um motor DC não sabe em que posição está - ele só gira para um lado ou
 *   para o outro. Então o sketch ESTIMA a posição pelo tempo: se o motor
 *   ficou 300 ms girando para a direita, a cabeça está "300 ms à direita"
 *   do centro. Com isso ele faz a cabeça oscilar em volta do centro e, ao
 *   parar, gira de volta o tempo necessário para ela ficar de frente.
 *   É uma estimativa: a inércia do motor acumula um pequeno erro a cada
 *   parada. Se a cabeça for "fugindo" do centro, recentralize com ela
 *   desligada (girando à mão).
 *
 * Por que não existe nenhum delay() aqui: enquanto a cabeça gira, a placa
 * precisa continuar lendo a serial para obedecer o 'o' e o 'P' na hora.
 * Um delay() congelaria tudo. Em vez disso, cada parte confere com millis()
 * quanto tempo passou.
 */

// ----------------------------- Pinos -----------------------------------
const int PINO_PONTE_H_ENA = 3;
const int PINO_PONTE_H_IN1 = 4;
const int PINO_PONTE_H_IN2 = 5;
const int PINO_LED_VERMELHO = 9;
const int PINO_LED_AZUL = 10;

// ----------------------------- Cabeça ----------------------------------
// Velocidade do motor, de 0 a 255 (PWM no ENA). Se o motor só zumbir e
// não girar, aumente: a ponte H "come" cerca de 2 V da alimentação.
const int VELOCIDADE_CABECA = 200;

// Quanto tempo o motor gira do centro até cada lado. Aumente para a cabeça
// virar mais; diminua se ela bater em algum limite do boneco.
const long AMPLITUDE_GIRO_MS = 600;

// Pausa com o motor freado antes de inverter o sentido. Inverter de uma
// vez gera um pico de corrente que pode reiniciar o Arduino e força as
// engrenagens.
const unsigned long PAUSA_INVERSAO_MS = 120;

// Trava de segurança: se o Python travar e nunca mandar 'P', a cabeça para
// sozinha (e volta ao centro) depois desse tempo.
const unsigned long TEMPO_MAXIMO_GIRO_MS = 30000;

// ----------------------------- Olhos -----------------------------------
// Os LEDs acendem e apagam com um fade curto (cerca de 0,2 s).
const int BRILHO_MAXIMO = 255;
const int PASSO_BRILHO = 5;
const unsigned long INTERVALO_PASSO_BRILHO_MS = 4;

// ----------------------------- Estado ----------------------------------
enum EstadoCabeca { PARADA, GIRANDO, PAUSA, VOLTANDO_AO_CENTRO };

EstadoCabeca estadoCabeca = PARADA;
EstadoCabeca estadoAposPausa = PARADA;  // para onde ir quando a pausa acabar
int sentido = 1;                        // +1 = direita, -1 = esquerda
long posicaoEstimadaMs = 0;             // 0 = centro; + direita; - esquerda
unsigned long instanteUltimaAtualizacao = 0;
unsigned long instanteInicioPausa = 0;
unsigned long instanteInicioGiro = 0;

// Cada LED tem o próprio brilho, para o Sharingan e o Rinnegan acenderem
// só um deles.
int brilhoAtualVermelho = 0;
int brilhoDesejadoVermelho = 0;
int brilhoAtualAzul = 0;
int brilhoDesejadoAzul = 0;
unsigned long instanteUltimoPassoBrilho = 0;


void setup() {
  pinMode(PINO_PONTE_H_ENA, OUTPUT);
  pinMode(PINO_PONTE_H_IN1, OUTPUT);
  pinMode(PINO_PONTE_H_IN2, OUTPUT);
  pinMode(PINO_LED_VERMELHO, OUTPUT);
  pinMode(PINO_LED_AZUL, OUTPUT);

  frearMotor();
  analogWrite(PINO_LED_VERMELHO, 0);
  analogWrite(PINO_LED_AZUL, 0);

  Serial.begin(9600);
  // Avisa o Python que terminou de ligar (ver Arduino._aguardar_pronto).
  // O "v2" avisa o Python que esta versão sabe acender cada LED sozinho
  // ('V' e 'A'). Com o sketch antigo, que manda só "PRONTO", o Python acende
  // os dois LEDs no lugar.
  Serial.println("PRONTO v2");
}

void loop() {
  // A ordem importa: a posição precisa ser contabilizada ANTES de ler os
  // comandos. Se um 'P' frear o motor primeiro, o último instante em que
  // ele ainda girava nunca entra na conta - e esse erro, sempre para o
  // mesmo lado, vai entortando a cabeça a cada parada.
  atualizarPosicaoEstimada();
  lerComandos();
  atualizarOlhos();
  atualizarCabeca();
}


// Lê todos os caracteres que chegaram pela serial e executa cada um.
void lerComandos() {
  while (Serial.available() > 0) {
    char comando = Serial.read();

    if (comando == 'O') {
      definirLeds(BRILHO_MAXIMO, BRILHO_MAXIMO);
    }
    else if (comando == 'o') {
      definirLeds(0, 0);
    }
    else if (comando == 'V') {
      definirLeds(BRILHO_MAXIMO, 0);   // Sharingan: só o vermelho
    }
    else if (comando == 'A') {
      definirLeds(0, BRILHO_MAXIMO);   // Rinnegan: só o azul
    }
    else if (comando == 'G') {
      comecarGiro();
    }
    else if (comando == 'P') {
      voltarAoCentro();
    }
    // Qualquer outro caractere (como '\n') é ignorado.
  }
}


// ----------------------------- Olhos -----------------------------------
// Define o brilho que cada LED deve alcançar (o fade é feito aos poucos).
void definirLeds(int vermelho, int azul) {
  brilhoDesejadoVermelho = vermelho;
  brilhoDesejadoAzul = azul;
}

// Dá um passo de brilho em direção ao valor desejado.
int aproximar(int atual, int desejado) {
  if (atual < desejado) return min(atual + PASSO_BRILHO, desejado);
  return max(atual - PASSO_BRILHO, desejado);
}

// Aproxima o brilho de cada LED do valor desejado, um passo por vez.
void atualizarOlhos() {
  if (brilhoAtualVermelho == brilhoDesejadoVermelho &&
      brilhoAtualAzul == brilhoDesejadoAzul) return;
  if (millis() - instanteUltimoPassoBrilho < INTERVALO_PASSO_BRILHO_MS) return;
  instanteUltimoPassoBrilho = millis();

  brilhoAtualVermelho = aproximar(brilhoAtualVermelho, brilhoDesejadoVermelho);
  brilhoAtualAzul = aproximar(brilhoAtualAzul, brilhoDesejadoAzul);
  analogWrite(PINO_LED_VERMELHO, brilhoAtualVermelho);
  analogWrite(PINO_LED_AZUL, brilhoAtualAzul);
}


// ----------------------------- Motor -----------------------------------
// Liga o motor no sentido indicado (+1 direita, -1 esquerda).
void ligarMotor(int novoSentido) {
  digitalWrite(PINO_PONTE_H_IN1, novoSentido > 0 ? HIGH : LOW);
  digitalWrite(PINO_PONTE_H_IN2, novoSentido > 0 ? LOW : HIGH);
  analogWrite(PINO_PONTE_H_ENA, VELOCIDADE_CABECA);
}

// Freia o motor: com ENA ligado e IN1 = IN2, a ponte H curto-circuita os
// terminais do motor, que para na hora em vez de continuar girando solto.
void frearMotor() {
  digitalWrite(PINO_PONTE_H_IN1, LOW);
  digitalWrite(PINO_PONTE_H_IN2, LOW);
  analogWrite(PINO_PONTE_H_ENA, 255);
}

// Freia, espera PAUSA_INVERSAO_MS e depois segue no 'novoSentido'.
void pausarEDepois(EstadoCabeca proximoEstado, int novoSentido) {
  frearMotor();
  sentido = novoSentido;
  estadoAposPausa = proximoEstado;
  estadoCabeca = PAUSA;
  instanteInicioPausa = millis();
}


// ----------------------------- Cabeça ----------------------------------
void comecarGiro() {
  instanteInicioGiro = millis();

  if (estadoCabeca == GIRANDO) return;  // já está girando

  if (estadoCabeca == PAUSA) {           // já vai voltar a girar
    estadoAposPausa = GIRANDO;
    return;
  }

  if (estadoCabeca == PARADA) {
    // Também passa pela pausa: a cabeça pode ter acabado de frear vindo
    // da esquerda, e arrancar para a direita na hora seria uma inversão
    // brusca - o mesmo pico de corrente que a pausa existe para evitar.
    pausarEDepois(GIRANDO, 1);
    return;
  }

  // VOLTANDO_AO_CENTRO: volta a girar, no sentido em que já está.
  estadoCabeca = GIRANDO;
}

void voltarAoCentro() {
  if (estadoCabeca == PARADA) return;

  // Já está no centro: só freia, sem ligar o motor nem por um instante.
  if (posicaoEstimadaMs == 0) {
    frearMotor();
    estadoCabeca = PARADA;
    return;
  }

  // Sentido que leva a cabeça de volta para a posição 0 (o centro).
  int sentidoDoCentro = (posicaoEstimadaMs > 0) ? -1 : 1;

  if (estadoCabeca == PAUSA) {
    sentido = sentidoDoCentro;
    estadoAposPausa = VOLTANDO_AO_CENTRO;
  }
  else if (sentido == sentidoDoCentro) {
    estadoCabeca = VOLTANDO_AO_CENTRO;   // já está indo para o centro
  }
  else {
    pausarEDepois(VOLTANDO_AO_CENTRO, sentidoDoCentro);  // precisa inverter
  }
}

// Soma à posição o tempo em que o motor ficou ligado desde a última volta
// do loop(), no sentido em que ele estava girando.
void atualizarPosicaoEstimada() {
  unsigned long agora = millis();
  unsigned long passou = agora - instanteUltimaAtualizacao;
  instanteUltimaAtualizacao = agora;

  if (estadoCabeca == GIRANDO || estadoCabeca == VOLTANDO_AO_CENTRO) {
    posicaoEstimadaMs += sentido * (long)passou;
  }
}

void atualizarCabeca() {
  unsigned long agora = millis();

  switch (estadoCabeca) {
    case GIRANDO:
      if (agora - instanteInicioGiro > TEMPO_MAXIMO_GIRO_MS) {
        voltarAoCentro();  // trava de segurança
      }
      else if (sentido * posicaoEstimadaMs >= AMPLITUDE_GIRO_MS) {
        pausarEDepois(GIRANDO, -sentido);  // chegou no lado: inverte
      }
      break;

    case PAUSA:
      if (agora - instanteInicioPausa >= PAUSA_INVERSAO_MS) {
        estadoCabeca = estadoAposPausa;
        ligarMotor(sentido);
      }
      break;

    case VOLTANDO_AO_CENTRO:
      // Passou (ou chegou) no centro, vindo de qualquer um dos lados.
      if (sentido * posicaoEstimadaMs >= 0) {
        frearMotor();
        posicaoEstimadaMs = 0;
        estadoCabeca = PARADA;
      }
      break;

    case PARADA:
      break;
  }
}
