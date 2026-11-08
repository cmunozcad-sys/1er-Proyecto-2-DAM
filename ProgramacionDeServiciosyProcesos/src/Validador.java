import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class Validador {

    static final String CABECERA =
            "referencia,cliente,modelo,color,personalizacion,texto_bordado,logo_club,talla,cantidad";
    static final int COLUMNAS = 9;

    public static void main(String[] args) throws IOException, InterruptedException {

        PrintStream salida = new PrintStream(System.out, true, StandardCharsets.UTF_8);

        if (args.length > 0 && args[0].equals("--bloquear")) {
            Thread.sleep(60_000);
        }

        BufferedReader lector = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        List<String> lineas = new ArrayList<>();
        String linea;

        while ((linea = lector.readLine()) != null) {
            if (!linea.isBlank()) {
                lineas.add(linea);
            }
        }

        if (lineas.isEmpty()) {
            salida.println("ERROR: el fichero está vacío");
            System.exit(1);
        }

        String cabecera = lineas.get(0).replace("\"", "");
        if (!cabecera.equals(CABECERA)) {
            salida.println("ERROR: la cabecera no es la esperada");
            System.exit(1);
        }

        if (lineas.size() == 1) {
            salida.println("ERROR: el fichero no tiene líneas de pedido");
            System.exit(1);
        }

        int errores = 0;

        for (int i = 1; i < lineas.size(); i++) {
            int numeroLinea = i + 1;
            String[] columnas = partir(lineas.get(i));

            if (columnas.length != COLUMNAS) {
                salida.println("ERROR línea " + numeroLinea + ": tiene " + columnas.length
                        + " columnas y debe tener " + COLUMNAS);
                errores++;
                continue;
            }

            if (columnas[0].isEmpty() || columnas[1].isEmpty() || columnas[2].isEmpty()) {
                salida.println("ERROR línea " + numeroLinea + ": falta la referencia, el cliente o el modelo");
                errores++;
            }

            try {
                double talla = Double.parseDouble(columnas[7]);
                if (talla < 30 || talla > 48) {
                    salida.println("ERROR línea " + numeroLinea + ": la talla " + columnas[7]
                            + " está fuera de rango (30-48)");
                    errores++;
                }
            } catch (NumberFormatException e) {
                salida.println("ERROR línea " + numeroLinea + ": la talla '" + columnas[7] + "' no es un número");
                errores++;
            }

            try {
                int cantidad = Integer.parseInt(columnas[8]);
                if (cantidad <= 0) {
                    salida.println("ERROR línea " + numeroLinea + ": la cantidad debe ser mayor que 0");
                    errores++;
                }
            } catch (NumberFormatException e) {
                salida.println("ERROR línea " + numeroLinea + ": la cantidad '" + columnas[8]
                        + "' no es un número entero");
                errores++;
            }
        }

        if (errores > 0) {
            salida.println("Validación fallida: " + errores + " error(es)");
            System.exit(2);
        }

        salida.println("OK: " + (lineas.size() - 1) + " líneas de pedido correctas");
        System.exit(0);
    }

    static String[] partir(String linea) {
        List<String> columnas = new ArrayList<>();
        StringBuilder actual = new StringBuilder();
        boolean entreComillas = false;

        for (char c : linea.toCharArray()) {
            if (c == '"') {
                entreComillas = !entreComillas;
            } else if (c == ',' && !entreComillas) {
                columnas.add(actual.toString().trim());
                actual.setLength(0);
            } else {
                actual.append(c);
            }
        }
        columnas.add(actual.toString().trim());

        return columnas.toArray(new String[0]);
    }
}