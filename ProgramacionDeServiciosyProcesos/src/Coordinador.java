import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class Coordinador {

    static final int TIMEOUT_SEGUNDOS = 10;

    static int codigo;
    static String salida;
    static boolean timeout;

    public static void main(String[] args) throws IOException, InterruptedException {

        System.setOut(new PrintStream(System.out, true, StandardCharsets.UTF_8));

        String fichero = "datos/ficha_fabricacion.csv";
        String opcion = "";

        for (String arg : args) {
            if (arg.equals("--bloquear")) {
                opcion = "--bloquear";
            } else {
                fichero = arg;
            }
        }

        Files.createDirectories(Path.of("salida"));
        log("Coordinador: inicio con el fichero " + fichero);

        if (!Files.exists(Path.of(fichero))) {
            System.out.println("ERROR: no existe el fichero " + fichero);
            log("Coordinador: no existe el fichero, fin con código 30");
            System.exit(30);
        }

        List<String> lineas = Files.readAllLines(Path.of(fichero), StandardCharsets.UTF_8);

        System.out.println("1. VALIDADOR");
        ejecutar("Validador", lineas, opcion);
        System.out.println(salida);

        if (timeout) {
            log("Coordinador: cancelado por timeout, fin con código 20");
            System.exit(20);
        }
        if (codigo != 0) {
            log("Coordinador: pedido rechazado, fin con código 10");
            System.exit(10);
        }

        System.out.println("2. ANALIZADOR");
        List<String> pedidoValidado = new ArrayList<>();
        pedidoValidado.add("pedido válido");
        pedidoValidado.addAll(lineas);

        ejecutar("Analizador", pedidoValidado, "");
        System.out.println(salida);
        if (codigo != 0) {
            log("Coordinador: fallo del Analizador, fin con código 30");
            System.exit(30);
        }
        Files.writeString(Path.of("salida/resumen_pedido.txt"), salida, StandardCharsets.UTF_8);

        System.out.println("3. GENERADOR DE FICHAS");
        ejecutar("GeneradorInformacionTaller", List.of(salida.split("\n")), "");
        System.out.println(salida);
        if (codigo != 0) {
            log("Coordinador: fallo del Generador, fin con código 30");
            System.exit(30);
        }
        Files.writeString(Path.of("salida/fichas_taller.txt"), salida, StandardCharsets.UTF_8);

        log("Coordinador: todo correcto, fin con código 0");
        System.exit(0);
    }

    static void ejecutar(String clase, List<String> lineas, String opcion)
            throws IOException, InterruptedException {

        String java = System.getProperty("java.home") + "/bin/java";
        String classpath = System.getProperty("java.class.path");

        ProcessBuilder constructor;
        if (opcion.isEmpty()) {
            constructor = new ProcessBuilder(java, "-cp", classpath, clase);
        } else {
            constructor = new ProcessBuilder(java, "-cp", classpath, clase, opcion);
        }
        constructor.redirectErrorStream(true);

        long inicio = System.currentTimeMillis();
        Process proceso = constructor.start();

        BufferedWriter escritor = new BufferedWriter(
                new OutputStreamWriter(proceso.getOutputStream(), StandardCharsets.UTF_8));
        for (String linea : lineas) {
            escritor.write(linea);
            escritor.newLine();
        }
        escritor.close();

        boolean haTerminado = proceso.waitFor(TIMEOUT_SEGUNDOS, TimeUnit.SECONDS);
        long tiempo = System.currentTimeMillis() - inicio;

        if (!haTerminado) {
            proceso.destroyForcibly();
            timeout = true;
            codigo = -1;
            salida = "ERROR: " + clase + " no ha terminado en " + TIMEOUT_SEGUNDOS + " segundos y se ha detenido";
            log(clase + ": TIMEOUT | PID " + proceso.pid() + " | " + tiempo + " ms | proceso detenido");
            return;
        }

        BufferedReader lector = new BufferedReader(
                new InputStreamReader(proceso.getInputStream(), StandardCharsets.UTF_8));
        StringBuilder texto = new StringBuilder();
        String linea;
        while ((linea = lector.readLine()) != null) {
            texto.append(linea).append("\n");
        }
        lector.close();

        timeout = false;
        codigo = proceso.exitValue();
        salida = texto.toString().trim();
        log(clase + ": PID " + proceso.pid() + " | código " + codigo + " | " + tiempo + " ms");
    }

    static void log(String mensaje) throws IOException {
        String linea = LocalDateTime.now().withNano(0) + " | " + mensaje + "\n";
        Files.writeString(Path.of("salida/procesamiento.log"), linea, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }
}