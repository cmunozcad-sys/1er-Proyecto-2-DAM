import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class Analizador {

    static final int COLUMNAS = 9;

    static final int SALIDA_OK = 0;
    static final int ERROR_SIN_ENTRADA = 1;
    static final int ERROR_NO_VALIDADO = 2;
    static final int ERROR_LECTURA = 3;
    static final int ERROR_FORMATO = 4;

    public static void main(String[] args) {

        System.setOut(new PrintStream(System.out, true, StandardCharsets.UTF_8));
        System.setErr(new PrintStream(System.err, true, StandardCharsets.UTF_8));

        BufferedReader entrada = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));

        Map<String, String> clientes = new LinkedHashMap<>();
        Map<String, Integer> totales = new LinkedHashMap<>();
        Map<String, Map<Double, Integer>> tallas = new LinkedHashMap<>();
        Map<String, Map<String, Integer>> variantes = new LinkedHashMap<>();

        try {
            String primera = entrada.readLine();

            if (primera == null) {
                System.err.println("ERROR: no se ha recibido nada por stdin");
                System.exit(ERROR_SIN_ENTRADA);
            }

            if (!primera.replace("\uFEFF", "").trim().equals("pedido válido")) {
                System.err.println("ERROR: el pedido no viene validado");
                System.exit(ERROR_NO_VALIDADO);
            }

            if (entrada.readLine() == null) {
                System.err.println("ERROR: falta la cabecera del pedido");
                System.exit(ERROR_FORMATO);
            }

            String linea;
            int numeroLinea = 2;

            while ((linea = entrada.readLine()) != null) {
                numeroLinea++;

                if (linea.isBlank()) {
                    continue;
                }

                String[] columnas = partir(linea);

                if (columnas.length != COLUMNAS) {
                    System.err.println("ERROR línea " + numeroLinea + ": tiene " + columnas.length
                            + " columnas y debe tener " + COLUMNAS);
                    System.exit(ERROR_FORMATO);
                }

                String referencia = columnas[0];
                String cliente = columnas[1];
                String modelo = columnas[2];
                String color = columnas[3];
                String personalizacion = columnas[4];
                String textoBordado = columnas[5];

                double talla;
                int cantidad;
                try {
                    talla = Double.parseDouble(columnas[7]);
                    cantidad = Integer.parseInt(columnas[8]);
                } catch (NumberFormatException e) {
                    System.err.println("ERROR línea " + numeroLinea + ": talla o cantidad no numérica");
                    System.exit(ERROR_FORMATO);
                    return;
                }

                String variante = modelo + " | " + color + " | " + personalizacion + " | " + textoBordado;

                clientes.putIfAbsent(referencia, cliente);
                totales.merge(referencia, cantidad, Integer::sum);
                tallas.computeIfAbsent(referencia, r -> new TreeMap<>()).merge(talla, cantidad, Integer::sum);
                variantes.computeIfAbsent(referencia, r -> new LinkedHashMap<>()).merge(variante, cantidad, Integer::sum);
            }

        } catch (IOException e) {
            System.err.println("ERROR leyendo la entrada: " + e.getMessage());
            System.exit(ERROR_LECTURA);
        }

        if (totales.isEmpty()) {
            System.err.println("ERROR: el pedido no tiene líneas");
            System.exit(ERROR_FORMATO);
        }

        for (String referencia : totales.keySet()) {
            System.out.println("PEDIDO;" + referencia + ";" + clientes.get(referencia) + ";" + totales.get(referencia));

            for (Map.Entry<Double, Integer> t : tallas.get(referencia).entrySet()) {
                System.out.println("TALLA;" + referencia + ";" + formatearTalla(t.getKey()) + ";" + t.getValue());
            }

            for (Map.Entry<String, Integer> v : variantes.get(referencia).entrySet()) {
                System.out.println("VARIANTE;" + referencia + ";" + v.getKey() + ";" + v.getValue());
            }
        }

        System.exit(SALIDA_OK);
    }

    static String formatearTalla(double talla) {
        if (talla == Math.floor(talla)) {
            return String.valueOf((int) talla);
        }
        return String.valueOf(talla);
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