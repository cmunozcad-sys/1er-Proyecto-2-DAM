import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class GeneradorInformacionTaller {

    static final int SALIDA_OK = 0;
    static final int ERROR_SIN_ENTRADA = 1;
    static final int ERROR_LECTURA = 3;
    static final int ERROR_FORMATO = 4;

    static final String SEPARADOR = "==================================================";
    static final String LINEA = "--------------------------------------------------";

    public static void main(String[] args) {

        BufferedReader entrada = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));

        int fichas = 0;
        boolean fichaAbierta = false;

        try {
            String linea;
            int numeroLinea = 0;

            while ((linea = entrada.readLine()) != null) {
                numeroLinea++;

                if (linea.isBlank()) {
                    continue;
                }

                String[] partes = linea.split(";");

                if (partes[0].equals("PEDIDO") && partes.length == 4) {
                    if (fichaAbierta) {
                        System.out.println(SEPARADOR);
                        System.out.println();
                    }
                    System.out.println(SEPARADOR);
                    System.out.println("FICHA DE TALLER - PEDIDO " + partes[1]);
                    System.out.println("Cliente: " + partes[2]);
                    System.out.println("Total de pares: " + partes[3]);
                    System.out.println(LINEA);
                    System.out.println("Talla\tPares");
                    fichaAbierta = true;
                    fichas++;

                } else if (partes[0].equals("TALLA") && partes.length == 4 && fichaAbierta) {
                    System.out.println(partes[2] + "\t" + partes[3]);

                } else if (partes[0].equals("VARIANTE") && partes.length == 4 && fichaAbierta) {
                    System.out.println(LINEA);
                    System.out.println("Variante: " + partes[2]);
                    System.out.println("Pares de esta variante: " + partes[3]);

                } else {
                    System.err.println("ERROR línea " + numeroLinea + ": formato no reconocido: " + linea);
                    System.exit(ERROR_FORMATO);
                }
            }

        } catch (IOException e) {
            System.err.println("ERROR leyendo la entrada: " + e.getMessage());
            System.exit(ERROR_LECTURA);
        }

        if (fichas == 0) {
            System.err.println("ERROR: no se ha recibido ningún pedido por stdin");
            System.exit(ERROR_SIN_ENTRADA);
        }

        System.out.println(SEPARADOR);
        System.exit(SALIDA_OK);
    }
}
